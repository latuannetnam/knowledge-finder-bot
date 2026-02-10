"""Tests for bot handler with nlm-proxy streaming integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from knowledge_finder_bot.auth.graph_client import UserInfo
from knowledge_finder_bot.bot import create_agent_app
from knowledge_finder_bot.config import Settings
from knowledge_finder_bot.nlm.models import NLMChunk, NLMResponse
from knowledge_finder_bot.nlm.session import SessionStore


def create_mock_context(
    activity_type: str,
    text: str = None,
    aad_object_id: str = None,
):
    """Create a mock turn context for bot tests."""
    context = MagicMock()
    context.send_activity = AsyncMock()
    context.remove_recipient_mention.return_value = text

    context.activity = MagicMock()
    context.activity.type = activity_type
    context.activity.text = text
    context.activity.from_property = MagicMock()
    context.activity.from_property.name = "Test User"
    context.activity.from_property.aad_object_id = aad_object_id
    context.activity.recipient = MagicMock()
    context.activity.recipient.id = "bot-id"
    context.activity.members_added = None

    return context


def _make_default_chunks():
    """Standard chunk sequence: meta(model) -> reasoning -> content -> meta(conv_id) -> meta(finish)."""
    return [
        NLMChunk(chunk_type="meta", model="hr-notebook"),
        NLMChunk(chunk_type="reasoning", text="Looking in HR docs"),
        NLMChunk(chunk_type="content", text="The leave policy "),
        NLMChunk(chunk_type="content", text="allows 20 days per year."),
        NLMChunk(chunk_type="meta", conversation_id="conv-123"),
        NLMChunk(chunk_type="meta", finish_reason="stop"),
    ]


@pytest.fixture
def mock_nlm_client():
    """Mock NLMClient with query_stream returning async generator."""
    client = MagicMock()

    async def _default_stream(**kwargs):
        for chunk in _make_default_chunks():
            yield chunk

    client.query_stream = MagicMock(side_effect=lambda **kw: _default_stream(**kw))
    return client


@pytest.fixture
def mock_streaming_response():
    """Mock StreamingResponse capturing all method calls."""
    sr = MagicMock()
    sr.queue_informative_update = MagicMock()
    sr.queue_text_chunk = MagicMock()
    sr.end_stream = AsyncMock()
    sr.set_generated_by_ai_label = MagicMock()
    return sr


@pytest.fixture
def session_store():
    """Real SessionStore for testing multi-turn."""
    return SessionStore(ttl=300, maxsize=100)


@pytest.fixture
def nlm_app(settings, acl_config_path, mock_graph_client, mock_nlm_client, session_store):
    """Agent app with ACL + nlm-proxy streaming integration."""
    from knowledge_finder_bot.acl.service import ACLService

    acl_service = ACLService(acl_config_path)
    return create_agent_app(
        settings=settings,
        graph_client=mock_graph_client,
        acl_service=acl_service,
        nlm_client=mock_nlm_client,
        session_store=session_store,
    )


@pytest.mark.asyncio
async def test_streaming_query_stream_called(nlm_app, mock_nlm_client, mock_streaming_response):
    """query_stream is called with correct args when nlm_client configured."""
    context = create_mock_context(
        activity_type="message",
        text="What is the leave policy?",
        aad_object_id="test-aad-id",
    )

    with patch(
        "knowledge_finder_bot.bot.bot.StreamingResponse",
        return_value=mock_streaming_response,
    ):
        await nlm_app.on_turn(context)

    mock_nlm_client.query_stream.assert_called_once()
    call_kwargs = mock_nlm_client.query_stream.call_args.kwargs
    assert call_kwargs["user_message"] == "What is the leave policy?"
    assert "hr-notebook" in call_kwargs["allowed_notebooks"]


@pytest.mark.asyncio
async def test_streaming_content_sent_via_queue_text_chunk(nlm_app, mock_nlm_client, mock_streaming_response):
    """Content chunks are piped to StreamingResponse.queue_text_chunk."""
    context = create_mock_context(
        activity_type="message",
        text="Hello",
        aad_object_id="test-aad-id",
    )

    with patch(
        "knowledge_finder_bot.bot.bot.StreamingResponse",
        return_value=mock_streaming_response,
    ):
        await nlm_app.on_turn(context)

    text_calls = [
        call[0][0] for call in mock_streaming_response.queue_text_chunk.call_args_list
    ]
    # Should contain reasoning, separator, content chunks, and source attribution
    combined = "".join(text_calls)
    assert "Looking in HR docs" in combined  # reasoning
    assert "---" in combined  # separator
    assert "leave policy" in combined  # content
    assert "allows 20 days" in combined  # content


@pytest.mark.asyncio
async def test_streaming_informative_update_with_notebook_name(nlm_app, mock_nlm_client, mock_streaming_response):
    """queue_informative_update called with notebook name."""
    context = create_mock_context(
        activity_type="message",
        text="Hello",
        aad_object_id="test-aad-id",
    )

    with patch(
        "knowledge_finder_bot.bot.bot.StreamingResponse",
        return_value=mock_streaming_response,
    ):
        await nlm_app.on_turn(context)

    mock_streaming_response.queue_informative_update.assert_called_once()
    info_text = mock_streaming_response.queue_informative_update.call_args[0][0]
    assert "HR Docs" in info_text


@pytest.mark.asyncio
async def test_streaming_end_stream_called(nlm_app, mock_nlm_client, mock_streaming_response):
    """end_stream() is awaited after all chunks processed."""
    context = create_mock_context(
        activity_type="message",
        text="Hello",
        aad_object_id="test-aad-id",
    )

    with patch(
        "knowledge_finder_bot.bot.bot.StreamingResponse",
        return_value=mock_streaming_response,
    ):
        await nlm_app.on_turn(context)

    mock_streaming_response.end_stream.assert_awaited_once()


@pytest.mark.asyncio
async def test_streaming_source_attribution_appended(nlm_app, mock_nlm_client, mock_streaming_response):
    """Source attribution is the last text chunk before end_stream."""
    context = create_mock_context(
        activity_type="message",
        text="Hello",
        aad_object_id="test-aad-id",
    )

    with patch(
        "knowledge_finder_bot.bot.bot.StreamingResponse",
        return_value=mock_streaming_response,
    ):
        await nlm_app.on_turn(context)

    text_calls = [
        call[0][0] for call in mock_streaming_response.queue_text_chunk.call_args_list
    ]
    last_text = text_calls[-1]
    assert "*Source: HR Docs*" in last_text


@pytest.mark.asyncio
async def test_streaming_conversation_id_stored(nlm_app, mock_nlm_client, session_store, mock_streaming_response):
    """conversation_id from stream is stored in session for next turn."""
    context = create_mock_context(
        activity_type="message",
        text="First question",
        aad_object_id="test-aad-id",
    )

    with patch(
        "knowledge_finder_bot.bot.bot.StreamingResponse",
        return_value=mock_streaming_response,
    ):
        await nlm_app.on_turn(context)

    assert session_store.get("test-aad-id") == "conv-123"


@pytest.mark.asyncio
async def test_streaming_conversation_id_reused(nlm_app, mock_nlm_client, session_store, mock_streaming_response):
    """Stored conversation_id is passed to subsequent query_stream calls."""
    session_store.set("test-aad-id", "existing-conv")

    context = create_mock_context(
        activity_type="message",
        text="Follow-up question",
        aad_object_id="test-aad-id",
    )

    with patch(
        "knowledge_finder_bot.bot.bot.StreamingResponse",
        return_value=mock_streaming_response,
    ):
        await nlm_app.on_turn(context)

    call_kwargs = mock_nlm_client.query_stream.call_args.kwargs
    assert call_kwargs["conversation_id"] == "existing-conv"


@pytest.mark.asyncio
async def test_streaming_error_sends_error_message(nlm_app, mock_nlm_client, mock_streaming_response):
    """Exception during streaming sends error via end_stream."""
    async def _error_stream(**kwargs):
        yield NLMChunk(chunk_type="meta", model="hr-notebook")
        raise Exception("Stream broken")

    mock_nlm_client.query_stream = MagicMock(side_effect=lambda **kw: _error_stream(**kw))

    context = create_mock_context(
        activity_type="message",
        text="Hello",
        aad_object_id="test-aad-id",
    )

    with patch(
        "knowledge_finder_bot.bot.bot.StreamingResponse",
        return_value=mock_streaming_response,
    ):
        await nlm_app.on_turn(context)

    # Error message should be sent via queue_text_chunk + end_stream
    text_calls = [
        call[0][0] for call in mock_streaming_response.queue_text_chunk.call_args_list
    ]
    error_found = any("error" in t.lower() for t in text_calls)
    assert error_found, f"Error message not found in: {text_calls}"
    mock_streaming_response.end_stream.assert_awaited()


@pytest.mark.asyncio
async def test_fallback_to_echo_when_nlm_client_none(settings, acl_config_path, mock_graph_client):
    """Falls back to echo when nlm_client is None (unchanged behavior)."""
    from knowledge_finder_bot.acl.service import ACLService

    acl_service = ACLService(acl_config_path)
    app = create_agent_app(
        settings=settings,
        graph_client=mock_graph_client,
        acl_service=acl_service,
        nlm_client=None,
    )

    context = create_mock_context(
        activity_type="message",
        text="Hello!",
        aad_object_id="test-aad-id",
    )
    await app.on_turn(context)

    calls = context.send_activity.call_args_list
    echo_found = any(
        isinstance(c[0][0], str) and "Allowed notebooks" in c[0][0]
        for c in calls
    )
    assert echo_found, f"Echo fallback not found in: {calls}"
