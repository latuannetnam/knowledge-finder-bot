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
    sr.set_attachments = MagicMock()
    sr.set_citations = MagicMock()
    sr._is_streaming_channel = True
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
async def test_streaming_only_answer_in_text_chunks(nlm_app, mock_nlm_client, mock_streaming_response):
    """Only content chunks are streamed — reasoning is excluded from text."""
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
    combined = "".join(text_calls)
    # Content should be present
    assert "leave policy" in combined
    assert "allows 20 days" in combined
    # Reasoning must NOT leak into text stream
    assert "Looking in HR docs" not in combined


@pytest.mark.asyncio
async def test_streaming_informative_updates_notebook_and_reasoning(nlm_app, mock_nlm_client, mock_streaming_response):
    """Two informative updates: notebook search + analyzing question."""
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

    info_calls = [
        call[0][0] for call in mock_streaming_response.queue_informative_update.call_args_list
    ]
    assert len(info_calls) == 2
    assert "HR Docs" in info_calls[0]
    assert "Analyzing" in info_calls[1]


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
async def test_streaming_source_via_citations_api(nlm_app, mock_nlm_client, mock_streaming_response):
    """Source attribution uses set_citations() with [doc1] marker in text."""
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

    # set_citations called with one Citation
    mock_streaming_response.set_citations.assert_called_once()
    citations = mock_streaming_response.set_citations.call_args[0][0]
    assert len(citations) == 1
    assert citations[0].title == "HR Docs"

    # Text must contain [doc1] marker for citation rendering
    text_calls = [
        call[0][0] for call in mock_streaming_response.queue_text_chunk.call_args_list
    ]
    combined = "".join(text_calls)
    assert "[doc1]" in combined


@pytest.mark.asyncio
async def test_streaming_reasoning_in_adaptive_card(nlm_app, mock_nlm_client, mock_streaming_response):
    """Reasoning text sent as collapsible Adaptive Card attachment."""
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

    mock_streaming_response.set_attachments.assert_called_once()
    attachments = mock_streaming_response.set_attachments.call_args[0][0]
    assert len(attachments) == 1
    assert attachments[0].content_type == "application/vnd.microsoft.card.adaptive"

    card_body = attachments[0].content["body"]
    reasoning_container = card_body[1]
    assert reasoning_container["id"] == "reasoning-container"
    assert reasoning_container["isVisible"] is False
    assert "Looking in HR docs" in reasoning_container["items"][0]["text"]


@pytest.mark.asyncio
async def test_streaming_no_reasoning_no_card(nlm_app, mock_nlm_client, mock_streaming_response):
    """When no reasoning chunks arrive, no Adaptive Card is attached."""
    async def _content_only_stream(**kwargs):
        yield NLMChunk(chunk_type="meta", model="hr-notebook")
        yield NLMChunk(chunk_type="content", text="Direct answer.")
        yield NLMChunk(chunk_type="meta", conversation_id="conv-456")
        yield NLMChunk(chunk_type="meta", finish_reason="stop")

    mock_nlm_client.query_stream = MagicMock(
        side_effect=lambda **kw: _content_only_stream(**kw)
    )

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

    mock_streaming_response.set_attachments.assert_not_called()


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
    """Exception during streaming sends error via context.send_activity."""
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

    # Error message should be sent via context.send_activity
    send_calls = [
        call[0][0] for call in context.send_activity.call_args_list
        if isinstance(call[0][0], str)
    ]
    error_found = any("error" in t.lower() for t in send_calls)
    assert error_found, f"Error message not found in: {send_calls}"


@pytest.mark.asyncio
async def test_buffered_mode_answer_without_reasoning(nlm_app, mock_nlm_client):
    """Non-streaming: answer in text, reasoning excluded from text body."""
    mock_sr = MagicMock()
    mock_sr._is_streaming_channel = False
    mock_sr.set_generated_by_ai_label = MagicMock()

    context = create_mock_context(
        activity_type="message",
        text="What is the leave policy?",
        aad_object_id="test-aad-id",
    )

    with patch(
        "knowledge_finder_bot.bot.bot.StreamingResponse",
        return_value=mock_sr,
    ):
        await nlm_app.on_turn(context)

    # Find the Activity object sent (skip typing indicator)
    activity_calls = [
        call[0][0] for call in context.send_activity.call_args_list
        if hasattr(call[0][0], "text") and getattr(call[0][0], "type", None) == "message"
    ]
    assert len(activity_calls) == 1
    response = activity_calls[0]

    # Answer text present, reasoning excluded
    assert "leave policy" in response.text
    assert "allows 20 days" in response.text
    assert "Looking in HR docs" not in response.text

    # Reasoning in Adaptive Card attachment
    assert response.attachments is not None
    assert len(response.attachments) == 1
    assert response.attachments[0].content_type == "application/vnd.microsoft.card.adaptive"


@pytest.mark.asyncio
async def test_buffered_mode_includes_source_attribution(nlm_app, mock_nlm_client):
    """Non-streaming buffered response includes text-based source attribution."""
    mock_sr = MagicMock()
    mock_sr._is_streaming_channel = False
    mock_sr.set_generated_by_ai_label = MagicMock()

    context = create_mock_context(
        activity_type="message",
        text="Hello",
        aad_object_id="test-aad-id",
    )

    with patch(
        "knowledge_finder_bot.bot.bot.StreamingResponse",
        return_value=mock_sr,
    ):
        await nlm_app.on_turn(context)

    # Find the Activity object sent
    activity_calls = [
        call[0][0] for call in context.send_activity.call_args_list
        if hasattr(call[0][0], "text") and getattr(call[0][0], "type", None) == "message"
    ]
    assert len(activity_calls) == 1
    assert "Source: HR Docs" in activity_calls[0].text


@pytest.mark.asyncio
async def test_buffered_mode_error_sends_error_message(nlm_app, mock_nlm_client):
    """Non-streaming error sends error via context.send_activity."""
    async def _error_stream(**kwargs):
        yield NLMChunk(chunk_type="meta", model="hr-notebook")
        raise Exception("Stream broken")

    mock_nlm_client.query_stream = MagicMock(side_effect=lambda **kw: _error_stream(**kw))

    mock_sr = MagicMock()
    mock_sr._is_streaming_channel = False
    mock_sr.set_generated_by_ai_label = MagicMock()

    context = create_mock_context(
        activity_type="message",
        text="Hello",
        aad_object_id="test-aad-id",
    )

    with patch(
        "knowledge_finder_bot.bot.bot.StreamingResponse",
        return_value=mock_sr,
    ):
        await nlm_app.on_turn(context)

    send_calls = [
        call[0][0] for call in context.send_activity.call_args_list
        if isinstance(call[0][0], str)
    ]
    error_found = any("error" in t.lower() for t in send_calls)
    assert error_found, f"Error message not found in: {send_calls}"


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
