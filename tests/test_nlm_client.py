"""Tests for nlm-proxy client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk

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


@pytest.fixture
def mock_llm():
    """Create a MagicMock that replaces ChatOpenAI for testing."""
    return MagicMock()


def _make_ai_message(content="", reasoning=None, model=None, finish_reason=None):
    """Build an AIMessage matching Langchain response format."""
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


def _make_ai_chunk(content="", reasoning=None, model=None, finish_reason=None):
    """Build an AIMessageChunk matching Langchain streaming format."""
    additional_kwargs = {}
    if reasoning is not None:
        additional_kwargs["reasoning_content"] = reasoning

    response_metadata = {}
    if model is not None:
        response_metadata["model_name"] = model
    if finish_reason is not None:
        response_metadata["finish_reason"] = finish_reason

    return AIMessageChunk(
        content=content,
        additional_kwargs=additional_kwargs,
        response_metadata=response_metadata,
    )


@pytest.mark.asyncio
async def test_non_streaming_query_success(nlm_settings, mock_llm):
    """Non-streaming query returns NLMResponse with parsed fields."""
    client = NLMClient(nlm_settings)
    client._llm = mock_llm

    mock_response = _make_ai_message(
        content="The answer is 42.",
        reasoning="Used hr-notebook",
        model="knowledge-finder",
        finish_reason="stop",
    )
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

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
async def test_non_streaming_passes_metadata(nlm_settings, mock_llm):
    """allowed_notebooks and chat_id passed as extra_body to ainvoke."""
    client = NLMClient(nlm_settings)
    client._llm = mock_llm

    mock_response = _make_ai_message(
        content="Answer",
        model="knowledge-finder",
        finish_reason="stop",
    )
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    await client.query(
        user_message="Test",
        allowed_notebooks=["nb-1", "nb-2"],
        chat_id="user-aad-123",
        stream=False,
    )

    call_kwargs = mock_llm.ainvoke.call_args.kwargs
    assert call_kwargs["extra_body"]["metadata"]["allowed_notebooks"] == ["nb-1", "nb-2"]
    assert call_kwargs["extra_body"]["metadata"]["chat_id"] == "user-aad-123"


@pytest.mark.asyncio
async def test_streaming_query_success(nlm_settings, mock_llm):
    """Streaming query buffers chunks into NLMResponse."""
    client = NLMClient(nlm_settings)
    client._llm = mock_llm

    chunks = [
        _make_ai_chunk(reasoning="Routing to ", model="knowledge-finder"),
        _make_ai_chunk(reasoning="hr-notebook"),
        _make_ai_chunk(content="The answer "),
        _make_ai_chunk(content="is 42."),
        _make_ai_chunk(finish_reason="stop"),
    ]

    async def mock_astream(*args, **kwargs):
        for chunk in chunks:
            yield chunk

    mock_llm.astream = mock_astream

    result = await client.query(
        user_message="What is the answer?",
        allowed_notebooks=["hr-notebook"],
        stream=True,
    )

    assert result.answer == "The answer is 42."
    assert result.reasoning == "Routing to hr-notebook"
    assert result.finish_reason == "stop"


@pytest.mark.asyncio
async def test_query_error_reraises(nlm_settings, mock_llm):
    """Client errors are logged and re-raised."""
    client = NLMClient(nlm_settings)
    client._llm = mock_llm

    mock_llm.ainvoke = AsyncMock(side_effect=Exception("Connection refused"))

    with pytest.raises(Exception, match="Connection refused"):
        await client.query(
            user_message="Test",
            allowed_notebooks=["nb-1"],
            stream=False,
        )


@pytest.mark.asyncio
async def test_non_streaming_no_reasoning(nlm_settings, mock_llm):
    """Non-streaming query works when no reasoning_content is present."""
    client = NLMClient(nlm_settings)
    client._llm = mock_llm

    mock_response = _make_ai_message(
        content="Simple answer",
        model="knowledge-finder",
        finish_reason="stop",
    )
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    result = await client.query(
        user_message="Simple question",
        allowed_notebooks=["nb-1"],
        stream=False,
    )

    assert result.answer == "Simple answer"
    assert result.reasoning is None
    assert result.finish_reason == "stop"


@pytest.mark.asyncio
async def test_query_stores_exchange_in_memory(nlm_settings, mock_llm):
    """Query stores Q&A exchange in memory when memory and session_id provided."""
    from knowledge_finder_bot.nlm.memory import ConversationMemoryManager

    memory = ConversationMemoryManager(ttl=3600, maxsize=100)
    client = NLMClient(nlm_settings, memory=memory)
    client._llm = mock_llm

    mock_response = _make_ai_message(
        content="The answer is 42.",
        model="knowledge-finder",
        finish_reason="stop",
    )
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

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
async def test_query_without_memory_still_works(nlm_settings, mock_llm):
    """Query works normally when no memory manager is provided."""
    client = NLMClient(nlm_settings)  # no memory
    client._llm = mock_llm

    mock_response = _make_ai_message(
        content="Answer",
        model="knowledge-finder",
        finish_reason="stop",
    )
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    result = await client.query(
        user_message="Test",
        allowed_notebooks=["nb-1"],
        session_id="test-session",
        stream=False,
    )

    assert result.answer == "Answer"


@pytest.mark.asyncio
async def test_query_without_session_id_skips_memory(nlm_settings, mock_llm):
    """Query does not store exchange when session_id is not provided."""
    from knowledge_finder_bot.nlm.memory import ConversationMemoryManager

    memory = ConversationMemoryManager(ttl=3600, maxsize=100)
    client = NLMClient(nlm_settings, memory=memory)
    client._llm = mock_llm

    mock_response = _make_ai_message(
        content="Answer",
        model="knowledge-finder",
        finish_reason="stop",
    )
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    await client.query(
        user_message="Test",
        allowed_notebooks=["nb-1"],
        # no session_id
        stream=False,
    )

    # Memory should be empty since no session_id was provided
    assert memory.get_messages("any-session") == []


@pytest.mark.asyncio
async def test_rewrite_called_when_history_exists(nlm_settings, mock_llm):
    """Question is rewritten when session has conversation history."""
    from knowledge_finder_bot.nlm.memory import ConversationMemoryManager

    memory = ConversationMemoryManager(ttl=3600, maxsize=100)
    client = NLMClient(nlm_settings, memory=memory, enable_rewrite=True)
    client._llm = mock_llm

    # Seed history
    memory.add_exchange("s1", "What is corporate entrepreneurship?", "It refers to...")

    # Mock rewrite response (ainvoke called for rewrite)
    rewrite_response = _make_ai_message(
        content="What are the different types of corporate entrepreneurship?",
        model="knowledge-finder",
        finish_reason="stop",
    )
    # Mock query response
    query_response = _make_ai_message(
        content="There are three types...",
        model="knowledge-finder",
        finish_reason="stop",
    )
    # ainvoke called twice: once for rewrite, once for non-streaming query
    mock_llm.ainvoke = AsyncMock(side_effect=[rewrite_response, query_response])

    result = await client.query(
        user_message="Tell me more about the types",
        allowed_notebooks=["nb-1"],
        session_id="s1",
        stream=False,
    )

    assert result.rewritten_question == "What are the different types of corporate entrepreneurship?"
    assert result.answer == "There are three types..."
    assert mock_llm.ainvoke.call_count == 2


@pytest.mark.asyncio
async def test_rewrite_skipped_when_no_history(nlm_settings, mock_llm):
    """No rewrite attempt when session has no history."""
    from knowledge_finder_bot.nlm.memory import ConversationMemoryManager

    memory = ConversationMemoryManager(ttl=3600, maxsize=100)
    client = NLMClient(nlm_settings, memory=memory, enable_rewrite=True)
    client._llm = mock_llm

    mock_response = _make_ai_message(
        content="Answer",
        model="knowledge-finder",
        finish_reason="stop",
    )
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    result = await client.query(
        user_message="What is X?",
        allowed_notebooks=["nb-1"],
        session_id="new-session",
        stream=False,
    )

    assert result.rewritten_question is None
    # Only 1 call (direct query, no rewrite)
    assert mock_llm.ainvoke.call_count == 1


@pytest.mark.asyncio
async def test_rewrite_skipped_when_disabled(nlm_settings, mock_llm):
    """No rewrite when enable_rewrite is False."""
    from knowledge_finder_bot.nlm.memory import ConversationMemoryManager

    memory = ConversationMemoryManager(ttl=3600, maxsize=100)
    client = NLMClient(nlm_settings, memory=memory, enable_rewrite=False)
    client._llm = mock_llm

    # Seed history
    memory.add_exchange("s1", "Q1", "A1")

    mock_response = _make_ai_message(
        content="Answer",
        model="knowledge-finder",
        finish_reason="stop",
    )
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    result = await client.query(
        user_message="Tell me more",
        allowed_notebooks=["nb-1"],
        session_id="s1",
        stream=False,
    )

    assert result.rewritten_question is None
    assert mock_llm.ainvoke.call_count == 1


@pytest.mark.asyncio
async def test_rewrite_failure_falls_back_to_original(nlm_settings, mock_llm):
    """If rewrite fails, original question is used."""
    from knowledge_finder_bot.nlm.memory import ConversationMemoryManager

    memory = ConversationMemoryManager(ttl=3600, maxsize=100)
    client = NLMClient(nlm_settings, memory=memory, enable_rewrite=True)
    client._llm = mock_llm

    memory.add_exchange("s1", "Q1", "A1")

    # First call (rewrite) fails, second call (query) succeeds
    query_response = _make_ai_message(
        content="Answer from original",
        model="knowledge-finder",
        finish_reason="stop",
    )
    mock_llm.ainvoke = AsyncMock(side_effect=[Exception("Rewrite failed"), query_response])

    result = await client.query(
        user_message="Tell me more",
        allowed_notebooks=["nb-1"],
        session_id="s1",
        stream=False,
    )

    assert result.rewritten_question is None
    assert result.answer == "Answer from original"
