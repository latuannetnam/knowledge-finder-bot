"""Tests for nlm-proxy client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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


@pytest.mark.asyncio
async def test_non_streaming_query_success(nlm_settings):
    """Non-streaming query returns NLMResponse with parsed fields."""
    client = NLMClient(nlm_settings)

    mock_message = MagicMock()
    mock_message.content = "The answer is 42."
    mock_message.reasoning_content = "Used hr-notebook"

    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_choice.finish_reason = "stop"

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.model = "knowledge-finder"
    mock_response.system_fingerprint = None

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
    """allowed_notebooks and chat_id passed in extra_body.metadata."""
    client = NLMClient(nlm_settings)

    mock_message = MagicMock()
    mock_message.content = "Answer"
    mock_message.reasoning_content = None

    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_choice.finish_reason = "stop"

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.model = "knowledge-finder"
    mock_response.system_fingerprint = None

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

    # Build mock chunks
    def make_chunk(content=None, reasoning=None, finish_reason=None,
                   model=None, system_fingerprint=None):
        delta = MagicMock()
        delta.content = content
        delta.reasoning_content = reasoning

        choice = MagicMock()
        choice.delta = delta
        choice.finish_reason = finish_reason

        chunk = MagicMock()
        chunk.choices = [choice]
        chunk.model = model
        chunk.system_fingerprint = system_fingerprint
        return chunk

    chunks = [
        make_chunk(reasoning="Routing to ", model="knowledge-finder"),
        make_chunk(reasoning="hr-notebook"),
        make_chunk(content="The answer "),
        make_chunk(content="is 42."),
        make_chunk(finish_reason="stop"),
    ]

    async def mock_stream():
        for chunk in chunks:
            yield chunk

    # AsyncOpenAI streaming returns an async context manager
    mock_stream_obj = mock_stream()
    client._client.chat.completions.create = AsyncMock(return_value=mock_stream_obj)

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
    client._client.chat.completions.create = AsyncMock(
        side_effect=Exception("Connection refused")
    )

    with pytest.raises(Exception, match="Connection refused"):
        await client.query(
            user_message="Test",
            allowed_notebooks=["nb-1"],
            stream=False,
        )
