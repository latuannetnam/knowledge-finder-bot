"""Tests for bot module with ACL enforcement."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from knowledge_finder_bot.auth.graph_client import UserInfo
from knowledge_finder_bot.bot import create_agent_app
from knowledge_finder_bot.config import Settings


def create_mock_context(
    activity_type: str,
    text: str = None,
    members_added: list = None,
    aad_object_id: str = None,
):
    """Create a mock turn context.

    The SDK accesses activity.text synchronously for regex matching,
    so we must use MagicMock (not AsyncMock) for the activity object.
    """
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
    context.activity.members_added = members_added

    return context


# --- Echo mode (no ACL) ---

@pytest.fixture
def echo_app(settings: Settings):
    """Agent app in echo-only mode (no Graph/ACL)."""
    return create_agent_app(settings, graph_client=None, acl_service=None)


@pytest.mark.asyncio
async def test_echo_mode_echoes_message(echo_app):
    context = create_mock_context(activity_type="message", text="Hello!")
    await echo_app.on_turn(context)

    calls = context.send_activity.call_args_list
    echo_found = any(
        isinstance(c[0][0], str) and "Hello!" in c[0][0]
        for c in calls
    )
    assert echo_found, f"Echo not found in: {calls}"


@pytest.mark.asyncio
async def test_welcome_message(echo_app):
    member = MagicMock()
    member.id = "new-user-id"
    context = create_mock_context(
        activity_type="conversationUpdate", members_added=[member]
    )
    await echo_app.on_turn(context)

    calls = context.send_activity.call_args_list
    welcome_found = any(
        isinstance(c[0][0], str) and "NotebookLM Bot" in c[0][0]
        for c in calls
    )
    assert welcome_found, f"Welcome not found in: {calls}"


# --- ACL mode ---

@pytest.fixture
def acl_app(settings, acl_config_path, mock_graph_client):
    """Agent app with ACL enforcement enabled."""
    from knowledge_finder_bot.acl.service import ACLService

    acl_service = ACLService(acl_config_path)
    return create_agent_app(
        settings=settings,
        graph_client=mock_graph_client,
        acl_service=acl_service,
    )


@pytest.mark.asyncio
async def test_acl_allowed_user_sees_notebooks(acl_app):
    """User in HR Team group should see hr-notebook and public-notebook."""
    context = create_mock_context(
        activity_type="message",
        text="What is the leave policy?",
        aad_object_id="test-aad-id",
    )
    await acl_app.on_turn(context)

    calls = context.send_activity.call_args_list
    response_found = any(
        isinstance(c[0][0], str) and "Allowed notebooks" in c[0][0]
        for c in calls
    )
    assert response_found, f"ACL response not found in: {calls}"


@pytest.mark.asyncio
async def test_acl_denied_user_gets_rejection(acl_app, mock_graph_client):
    """User with no matching groups gets rejection."""
    mock_graph_client.get_user_with_groups.return_value = UserInfo(
        aad_object_id="denied-user",
        display_name="Denied User",
        email="denied@co.com",
        groups=[
            {"id": "ffffffff-ffff-ffff-ffff-ffffffffffff", "display_name": "Unknown Group"},
        ],
    )

    context = create_mock_context(
        activity_type="message",
        text="Secret stuff",
        aad_object_id="denied-user",
    )
    await acl_app.on_turn(context)

    calls = context.send_activity.call_args_list
    # User should still get public-notebook via wildcard
    response_found = any(
        isinstance(c[0][0], str) and "Public KB" in c[0][0]
        for c in calls
    )
    assert response_found, f"Public notebook not found in: {calls}"


@pytest.mark.asyncio
async def test_missing_aad_object_id_gets_error(acl_app):
    """Message without aad_object_id gets identity error."""
    context = create_mock_context(
        activity_type="message",
        text="Hi",
        aad_object_id=None,
    )
    await acl_app.on_turn(context)

    calls = context.send_activity.call_args_list
    error_found = any(
        isinstance(c[0][0], str) and "Unable to identify" in c[0][0]
        for c in calls
    )
    assert error_found, f"Identity error not found in: {calls}"


@pytest.mark.asyncio
async def test_graph_api_failure_returns_graceful_error(acl_app, mock_graph_client):
    """Graph API exception results in graceful error message."""
    mock_graph_client.get_user_with_groups.side_effect = Exception("Graph API down")

    context = create_mock_context(
        activity_type="message",
        text="Hello",
        aad_object_id="failing-user",
    )
    await acl_app.on_turn(context)

    calls = context.send_activity.call_args_list
    error_found = any(
        isinstance(c[0][0], str) and "Unable to verify" in c[0][0]
        for c in calls
    )
    assert error_found, f"Graph error message not found in: {calls}"
