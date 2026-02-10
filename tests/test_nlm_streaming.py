"""Tests for NLMChunk model and query_stream."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from knowledge_finder_bot.nlm.client import NLMClient
from knowledge_finder_bot.nlm.models import NLMChunk


def test_nlm_chunk_content():
    """NLMChunk holds content chunk data."""
    chunk = NLMChunk(chunk_type="content", text="Hello")
    assert chunk.chunk_type == "content"
    assert chunk.text == "Hello"
    assert chunk.model is None


def test_nlm_chunk_meta():
    """NLMChunk holds meta chunk data."""
    chunk = NLMChunk(chunk_type="meta", model="hr-notebook", conversation_id="abc")
    assert chunk.chunk_type == "meta"
    assert chunk.model == "hr-notebook"
    assert chunk.conversation_id == "abc"
    assert chunk.text is None


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


def make_chunk(content=None, reasoning=None, finish_reason=None,
               model=None, system_fingerprint=None):
    """Build a mock SSE chunk matching OpenAI streaming format."""
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


async def _collect_chunks(gen):
    """Collect all chunks from an async generator into a list."""
    result = []
    async for chunk in gen:
        result.append(chunk)
    return result


@pytest.mark.asyncio
async def test_query_stream_yields_reasoning_chunks(nlm_settings):
    """Reasoning content arrives as chunk_type='reasoning'."""
    client = NLMClient(nlm_settings)

    chunks = [
        make_chunk(reasoning="Thinking about ", model="kf"),
        make_chunk(reasoning="the answer"),
        make_chunk(content="Result", finish_reason="stop"),
    ]

    async def mock_stream():
        for c in chunks:
            yield c

    client._client.chat.completions.create = AsyncMock(return_value=mock_stream())

    result = await _collect_chunks(client.query_stream(
        user_message="Test",
        allowed_notebooks=["nb-1"],
    ))

    reasoning_chunks = [c for c in result if c.chunk_type == "reasoning"]
    assert len(reasoning_chunks) == 2
    assert reasoning_chunks[0].text == "Thinking about "
    assert reasoning_chunks[1].text == "the answer"


@pytest.mark.asyncio
async def test_query_stream_yields_content_chunks(nlm_settings):
    """Answer content arrives as chunk_type='content'."""
    client = NLMClient(nlm_settings)

    chunks = [
        make_chunk(content="Hello ", model="kf"),
        make_chunk(content="world!", finish_reason="stop"),
    ]

    async def mock_stream():
        for c in chunks:
            yield c

    client._client.chat.completions.create = AsyncMock(return_value=mock_stream())

    result = await _collect_chunks(client.query_stream(
        user_message="Test",
        allowed_notebooks=["nb-1"],
    ))

    content_chunks = [c for c in result if c.chunk_type == "content"]
    assert len(content_chunks) == 2
    assert content_chunks[0].text == "Hello "
    assert content_chunks[1].text == "world!"


@pytest.mark.asyncio
async def test_query_stream_yields_model_meta(nlm_settings):
    """First chunk with model field yields a meta chunk."""
    client = NLMClient(nlm_settings)

    chunks = [
        make_chunk(reasoning="think", model="hr-notebook"),
        make_chunk(reasoning="more", model="hr-notebook"),  # second time - no duplicate meta
        make_chunk(finish_reason="stop"),
    ]

    async def mock_stream():
        for c in chunks:
            yield c

    client._client.chat.completions.create = AsyncMock(return_value=mock_stream())

    result = await _collect_chunks(client.query_stream(
        user_message="Test",
        allowed_notebooks=["nb-1"],
    ))

    model_metas = [c for c in result if c.chunk_type == "meta" and c.model is not None]
    assert len(model_metas) == 1
    assert model_metas[0].model == "hr-notebook"


@pytest.mark.asyncio
async def test_query_stream_yields_conversation_id(nlm_settings):
    """system_fingerprint='conv_xxx' yields meta chunk with conversation_id."""
    client = NLMClient(nlm_settings)

    chunks = [
        make_chunk(content="Hi", model="kf", system_fingerprint="conv_abc123"),
        make_chunk(finish_reason="stop"),
    ]

    async def mock_stream():
        for c in chunks:
            yield c

    client._client.chat.completions.create = AsyncMock(return_value=mock_stream())

    result = await _collect_chunks(client.query_stream(
        user_message="Test",
        allowed_notebooks=["nb-1"],
    ))

    conv_metas = [c for c in result if c.chunk_type == "meta" and c.conversation_id is not None]
    assert len(conv_metas) >= 1
    assert conv_metas[0].conversation_id == "abc123"


@pytest.mark.asyncio
async def test_query_stream_yields_finish_reason(nlm_settings):
    """Last chunk yields meta with finish_reason."""
    client = NLMClient(nlm_settings)

    chunks = [
        make_chunk(content="Done", model="kf"),
        make_chunk(finish_reason="stop"),
    ]

    async def mock_stream():
        for c in chunks:
            yield c

    client._client.chat.completions.create = AsyncMock(return_value=mock_stream())

    result = await _collect_chunks(client.query_stream(
        user_message="Test",
        allowed_notebooks=["nb-1"],
    ))

    finish_metas = [c for c in result if c.chunk_type == "meta" and c.finish_reason is not None]
    assert len(finish_metas) == 1
    assert finish_metas[0].finish_reason == "stop"


@pytest.mark.asyncio
async def test_query_stream_propagates_error(nlm_settings):
    """Exception during streaming propagates to caller."""
    client = NLMClient(nlm_settings)
    client._client.chat.completions.create = AsyncMock(
        side_effect=Exception("Connection refused")
    )

    with pytest.raises(Exception, match="Connection refused"):
        async for _ in client.query_stream(
            user_message="Test",
            allowed_notebooks=["nb-1"],
        ):
            pass


@pytest.mark.asyncio
async def test_query_stream_passes_metadata(nlm_settings):
    """allowed_notebooks and conversation_id passed in extra_body."""
    client = NLMClient(nlm_settings)

    async def mock_stream():
        yield make_chunk(content="ok", model="kf", finish_reason="stop")

    client._client.chat.completions.create = AsyncMock(return_value=mock_stream())

    async for _ in client.query_stream(
        user_message="Test",
        allowed_notebooks=["nb-1", "nb-2"],
        conversation_id="existing-conv",
    ):
        pass

    call_kwargs = client._client.chat.completions.create.call_args.kwargs
    assert call_kwargs["extra_body"]["metadata"]["allowed_notebooks"] == ["nb-1", "nb-2"]
    assert call_kwargs["extra_body"]["conversation_id"] == "existing-conv"
    assert call_kwargs["stream"] is True
