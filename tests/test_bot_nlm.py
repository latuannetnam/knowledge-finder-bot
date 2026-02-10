"""Tests for bot handler with nlm-proxy integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from knowledge_finder_bot.auth.graph_client import UserInfo
from knowledge_finder_bot.bot import create_agent_app
from knowledge_finder_bot.config import Settings
from knowledge_finder_bot.nlm.models import NLMResponse
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


@pytest.fixture
def mock_nlm_client():
    """Mock NLMClient that returns a configurable NLMResponse."""
    client = AsyncMock()
    client.query = AsyncMock(
        return_value=NLMResponse(
            answer="The leave policy allows 20 days per year.",
            reasoning="hr-notebook",
            model="knowledge-finder",
            conversation_id="conv-123",
            finish_reason="stop",
        )
    )
    return client


@pytest.fixture
def session_store():
    """Real SessionStore for testing multi-turn."""
    return SessionStore(ttl=300, maxsize=100)


@pytest.fixture
def nlm_app(settings, acl_config_path, mock_graph_client, mock_nlm_client, session_store):
    """Agent app with ACL + nlm-proxy integration."""
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
async def test_nlm_query_called_when_configured(nlm_app, mock_nlm_client):
    """Message handler queries nlm-proxy when nlm_client is configured."""
    context = create_mock_context(
        activity_type="message",
        text="What is the leave policy?",
        aad_object_id="test-aad-id",
    )
    await nlm_app.on_turn(context)

    mock_nlm_client.query.assert_called_once()
    call_kwargs = mock_nlm_client.query.call_args.kwargs
    assert call_kwargs["user_message"] == "What is the leave policy?"
    assert "hr-notebook" in call_kwargs["allowed_notebooks"]


@pytest.mark.asyncio
async def test_fallback_to_echo_when_nlm_client_none(settings, acl_config_path, mock_graph_client):
    """Falls back to echo when nlm_client is None."""
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


@pytest.mark.asyncio
async def test_typing_indicator_sent_before_query(nlm_app, mock_nlm_client):
    """Typing indicator is sent before the nlm-proxy query."""
    context = create_mock_context(
        activity_type="message",
        text="Hello",
        aad_object_id="test-aad-id",
    )
    await nlm_app.on_turn(context)

    calls = context.send_activity.call_args_list
    # First send_activity call should be the typing indicator (Activity object)
    typing_found = any(
        not isinstance(c[0][0], str) and getattr(c[0][0], "type", None) == "typing"
        for c in calls
    )
    assert typing_found, f"Typing indicator not found in: {calls}"


@pytest.mark.asyncio
async def test_multi_turn_conversation_id_stored(
    nlm_app, mock_nlm_client, session_store
):
    """conversation_id from nlm response is stored for next turn."""
    context = create_mock_context(
        activity_type="message",
        text="First question",
        aad_object_id="test-aad-id",
    )
    await nlm_app.on_turn(context)

    # Session store should now have the conversation_id
    assert session_store.get("test-aad-id") == "conv-123"


@pytest.mark.asyncio
async def test_multi_turn_conversation_id_reused(
    nlm_app, mock_nlm_client, session_store
):
    """Stored conversation_id is passed to subsequent queries."""
    # Pre-populate session
    session_store.set("test-aad-id", "existing-conv")

    context = create_mock_context(
        activity_type="message",
        text="Follow-up question",
        aad_object_id="test-aad-id",
    )
    await nlm_app.on_turn(context)

    call_kwargs = mock_nlm_client.query.call_args.kwargs
    assert call_kwargs["conversation_id"] == "existing-conv"


@pytest.mark.asyncio
async def test_nlm_error_returns_user_friendly_message(nlm_app, mock_nlm_client):
    """nlm-proxy failure results in user-friendly error message."""
    mock_nlm_client.query.side_effect = Exception("Connection refused")

    context = create_mock_context(
        activity_type="message",
        text="Hello",
        aad_object_id="test-aad-id",
    )
    await nlm_app.on_turn(context)

    calls = context.send_activity.call_args_list
    error_found = any(
        isinstance(c[0][0], str) and "encountered an error" in c[0][0]
        for c in calls
    )
    assert error_found, f"Error message not found in: {calls}"


@pytest.mark.asyncio
async def test_response_formatted_and_sent(nlm_app, mock_nlm_client):
    """nlm response is formatted and sent to user."""
    context = create_mock_context(
        activity_type="message",
        text="What is the leave policy?",
        aad_object_id="test-aad-id",
    )
    await nlm_app.on_turn(context)

    calls = context.send_activity.call_args_list
    answer_found = any(
        isinstance(c[0][0], str) and "leave policy allows 20 days" in c[0][0]
        for c in calls
    )
    assert answer_found, f"Formatted answer not found in: {calls}"
