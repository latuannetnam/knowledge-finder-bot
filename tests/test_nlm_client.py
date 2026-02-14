"""Tests for nlm-proxy client."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from knowledge_finder_bot.nlm.client import NLMClient
from knowledge_finder_bot.nlm.models import NLMResponse


@pytest.fixture
def nlm_settings(mock_env_vars):
    """Settings with nlm-proxy configured."""
    from knowledge_finder_bot.config import Settings

    with patch.dict("os.environ", {
        **mock_env_vars,
        "NLM_PROXY_URL": "http://localhost:8000/v1",
        "NLM_PROXY_API_KEY": "test-key",
    }):
        return Settings()


def _make_ai_message(content="", reasoning=None, model=None, finish_reason=None):
    """Build an AIMessage for LangChain-based methods (rewrite, followup)."""
    additional_kwargs = {}
    if reasoning is not None:
        additional_kwargs["reasoning_content"] = reasoning

    response_metadata = {}
    if model is not None:
        response_metadata["model_name"] = model
    if finish_reason is not None:
        response_metadata["finish_reason"] = finish_reason

    return AIMessage(
        content=content,
        additional_kwargs=additional_kwargs,
        response_metadata=response_metadata,
    )


def _make_raw_response(content="", reasoning=None, model="knowledge-finder", finish_reason="stop"):
    """Build a raw OpenAI SDK non-streaming response."""
    message = SimpleNamespace(
        content=content,
        reasoning_content=reasoning,
        role="assistant",
    )
    choice = SimpleNamespace(
        message=message,
        finish_reason=finish_reason,
        index=0,
    )
    return SimpleNamespace(
        model=model,
        choices=[choice],
    )


def _make_raw_chunk(content=None, reasoning=None, model=None, finish_reason=None):
    """Build a raw OpenAI SDK streaming chunk."""
    delta = SimpleNamespace(
        content=content,
        reasoning_content=reasoning,
        role="assistant" if content or reasoning else None,
    )
    choice = SimpleNamespace(
        delta=delta,
        finish_reason=finish_reason,
        index=0,
    )
    return SimpleNamespace(
        model=model,
        choices=[choice],
    )


def _make_mock_stream(chunks):
    """Create an async iterator that yields raw chunks, wrapped in a coroutine."""
    async def _stream():
        for c in chunks:
            yield c

    async def mock_create(*args, **kwargs):
        return _stream()

    return mock_create


@pytest.mark.asyncio
async def test_non_streaming_query_success(nlm_settings):
    """Non-streaming query returns NLMResponse with parsed fields."""
    client = NLMClient(nlm_settings)

    mock_response = _make_raw_response(
        content="The answer is 42.",
        reasoning="Used hr-notebook",
        model="knowledge-finder",
        finish_reason="stop",
    )
    client._client = MagicMock()
    client._client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await client.query(
        user_message="What is the answer?",
        allowed_notebooks=["hr-notebook"],
        stream=False,
    )

    assert isinstance(result, NLMResponse)
    assert result.answer == "The answer is 42."
    assert result.reasoning == "Used hr-notebook"
    assert result.model == "knowledge-finder"
    assert result.finish_reason == "stop"


@pytest.mark.asyncio
async def test_non_streaming_passes_metadata(nlm_settings):
    """allowed_notebooks and chat_id passed as extra_body."""
    client = NLMClient(nlm_settings)

    mock_response = _make_raw_response(content="Answer")
    client._client = MagicMock()
    client._client.chat.completions.create = AsyncMock(return_value=mock_response)

    await client.query(
        user_message="Test",
        allowed_notebooks=["nb-1", "nb-2"],
        chat_id="user-aad-123",
        stream=False,
    )

    call_kwargs = client._client.chat.completions.create.call_args.kwargs
    assert call_kwargs["extra_body"]["metadata"]["allowed_notebooks"] == ["nb-1", "nb-2"]
    assert call_kwargs["extra_body"]["metadata"]["chat_id"] == "user-aad-123"


@pytest.mark.asyncio
async def test_streaming_query_success(nlm_settings):
    """Streaming query buffers chunks into NLMResponse."""
    client = NLMClient(nlm_settings)

    chunks = [
        _make_raw_chunk(reasoning="Routing to ", model="knowledge-finder"),
        _make_raw_chunk(reasoning="hr-notebook"),
        _make_raw_chunk(content="The answer "),
        _make_raw_chunk(content="is 42."),
        _make_raw_chunk(finish_reason="stop"),
    ]

    client._client = MagicMock()
    client._client.chat.completions.create = AsyncMock(side_effect=_make_mock_stream(chunks))

    result = await client.query(
        user_message="What is the answer?",
        allowed_notebooks=["hr-notebook"],
        stream=True,
    )

    assert result.answer == "The answer is 42."
    assert result.reasoning == "Routing to hr-notebook"
    assert result.finish_reason == "stop"


@pytest.mark.asyncio
async def test_query_error_reraises(nlm_settings):
    """Client errors are logged and re-raised."""
    client = NLMClient(nlm_settings)

    client._client = MagicMock()
    client._client.chat.completions.create = AsyncMock(side_effect=Exception("Connection refused"))

    with pytest.raises(Exception, match="Connection refused"):
        await client.query(
            user_message="Test",
            allowed_notebooks=["nb-1"],
            stream=False,
        )


@pytest.mark.asyncio
async def test_non_streaming_no_reasoning(nlm_settings):
    """Non-streaming query works when no reasoning_content is present."""
    client = NLMClient(nlm_settings)

    mock_response = _make_raw_response(content="Simple answer", reasoning=None)
    client._client = MagicMock()
    client._client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await client.query(
        user_message="Simple question",
        allowed_notebooks=["nb-1"],
        stream=False,
    )

    assert result.answer == "Simple answer"
    assert result.reasoning is None
    assert result.finish_reason == "stop"


@pytest.mark.asyncio
async def test_query_stores_exchange_in_memory(nlm_settings):
    """Query stores Q&A exchange in memory when memory and session_id provided."""
    from knowledge_finder_bot.nlm.memory import ConversationMemoryManager

    memory = ConversationMemoryManager(ttl=3600, maxsize=100)
    client = NLMClient(nlm_settings, memory=memory)

    mock_response = _make_raw_response(content="The answer is 42.")
    client._client = MagicMock()
    client._client.chat.completions.create = AsyncMock(return_value=mock_response)

    await client.query(
        user_message="What is the answer?",
        allowed_notebooks=["nb-1"],
        session_id="test-session",
        stream=False,
    )

    messages = memory.get_messages("test-session")
    assert len(messages) == 2
    assert messages[0].content == "What is the answer?"
    assert messages[1].content == "The answer is 42."


@pytest.mark.asyncio
async def test_query_without_memory_still_works(nlm_settings):
    """Query works normally when no memory manager is provided."""
    client = NLMClient(nlm_settings)  # no memory

    mock_response = _make_raw_response(content="Answer")
    client._client = MagicMock()
    client._client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await client.query(
        user_message="Test",
        allowed_notebooks=["nb-1"],
        session_id="test-session",
        stream=False,
    )

    assert result.answer == "Answer"


@pytest.mark.asyncio
async def test_query_without_session_id_skips_memory(nlm_settings):
    """Query does not store exchange when session_id is not provided."""
    from knowledge_finder_bot.nlm.memory import ConversationMemoryManager

    memory = ConversationMemoryManager(ttl=3600, maxsize=100)
    client = NLMClient(nlm_settings, memory=memory)

    mock_response = _make_raw_response(content="Answer")
    client._client = MagicMock()
    client._client.chat.completions.create = AsyncMock(return_value=mock_response)

    await client.query(
        user_message="Test",
        allowed_notebooks=["nb-1"],
        # no session_id
        stream=False,
    )

    # Memory should be empty since no session_id was provided
    assert memory.get_messages("any-session") == []


@pytest.mark.asyncio
async def test_rewrite_called_when_history_exists(nlm_settings):
    """Question is rewritten when session has conversation history."""
    from knowledge_finder_bot.nlm.memory import ConversationMemoryManager

    memory = ConversationMemoryManager(ttl=3600, maxsize=100)
    client = NLMClient(nlm_settings, memory=memory, enable_rewrite=True)

    # Seed history
    memory.add_exchange("s1", "What is corporate entrepreneurship?", "It refers to...")

    # Mock rewrite response (ainvoke on _llm for rewrite)
    rewrite_response = _make_ai_message(
        content="What are the different types of corporate entrepreneurship?",
        model="knowledge-finder",
        finish_reason="stop",
    )
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=rewrite_response)
    client._llm = mock_llm

    # Mock query response (non-streaming on _client)
    query_response = _make_raw_response(content="There are three types...")
    client._client = MagicMock()
    client._client.chat.completions.create = AsyncMock(return_value=query_response)

    result = await client.query(
        user_message="Tell me more about the types",
        allowed_notebooks=["nb-1"],
        session_id="s1",
        stream=False,
    )

    assert result.rewritten_question == "What are the different types of corporate entrepreneurship?"
    assert result.answer == "There are three types..."
    assert mock_llm.ainvoke.call_count == 1  # rewrite only
    assert client._client.chat.completions.create.call_count == 1  # query


@pytest.mark.asyncio
async def test_rewrite_skipped_when_no_history(nlm_settings):
    """No rewrite attempt when session has no history."""
    from knowledge_finder_bot.nlm.memory import ConversationMemoryManager

    memory = ConversationMemoryManager(ttl=3600, maxsize=100)
    client = NLMClient(nlm_settings, memory=memory, enable_rewrite=True)

    mock_response = _make_raw_response(content="Answer")
    client._client = MagicMock()
    client._client.chat.completions.create = AsyncMock(return_value=mock_response)

    mock_llm = MagicMock()
    client._llm = mock_llm

    result = await client.query(
        user_message="What is X?",
        allowed_notebooks=["nb-1"],
        session_id="new-session",
        stream=False,
    )

    assert result.rewritten_question is None
    # No rewrite call
    mock_llm.ainvoke.assert_not_called()


@pytest.mark.asyncio
async def test_rewrite_skipped_when_disabled(nlm_settings):
    """No rewrite when enable_rewrite is False."""
    from knowledge_finder_bot.nlm.memory import ConversationMemoryManager

    memory = ConversationMemoryManager(ttl=3600, maxsize=100)
    client = NLMClient(nlm_settings, memory=memory, enable_rewrite=False)

    # Seed history
    memory.add_exchange("s1", "Q1", "A1")

    mock_response = _make_raw_response(content="Answer")
    client._client = MagicMock()
    client._client.chat.completions.create = AsyncMock(return_value=mock_response)

    mock_llm = MagicMock()
    client._llm = mock_llm

    result = await client.query(
        user_message="Tell me more",
        allowed_notebooks=["nb-1"],
        session_id="s1",
        stream=False,
    )

    assert result.rewritten_question is None
    mock_llm.ainvoke.assert_not_called()


@pytest.mark.asyncio
async def test_rewrite_failure_falls_back_to_original(nlm_settings):
    """If rewrite fails, original question is used."""
    from knowledge_finder_bot.nlm.memory import ConversationMemoryManager

    memory = ConversationMemoryManager(ttl=3600, maxsize=100)
    client = NLMClient(nlm_settings, memory=memory, enable_rewrite=True)

    memory.add_exchange("s1", "Q1", "A1")

    # Rewrite fails
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=Exception("Rewrite failed"))
    client._llm = mock_llm

    # Query succeeds
    query_response = _make_raw_response(content="Answer from original")
    client._client = MagicMock()
    client._client.chat.completions.create = AsyncMock(return_value=query_response)

    result = await client.query(
        user_message="Tell me more",
        allowed_notebooks=["nb-1"],
        session_id="s1",
        stream=False,
    )

    assert result.rewritten_question is None
    assert result.answer == "Answer from original"
