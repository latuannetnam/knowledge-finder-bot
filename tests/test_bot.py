"""Tests for bot module."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from knowledge_finder_bot.bot import create_agent_app
from knowledge_finder_bot.config import Settings


@pytest.fixture
def agent_app(settings: Settings):
    """Create agent application for testing."""
    return create_agent_app(settings)


def create_mock_context(activity_type: str, text: str = None, members_added: list = None):
    """Create a mock turn context with proper non-async attributes.

    The SDK accesses activity.text synchronously for regex matching,
    so we must use MagicMock (not AsyncMock) for the activity object.
    """
    # Create context with async methods
    context = MagicMock()
    context.send_activity = AsyncMock()

    # SDK calls remove_recipient_mention() to get the text for matching
    context.remove_recipient_mention.return_value = text

    # Activity must be a regular MagicMock to avoid async attribute access
    context.activity = MagicMock()
    context.activity.type = activity_type
    context.activity.text = text
    context.activity.from_property = MagicMock()
    context.activity.from_property.name = "Test User"
    context.activity.recipient = MagicMock()
    context.activity.recipient.id = "bot-id"
    context.activity.members_added = members_added

    return context


@pytest.mark.asyncio
async def test_on_message_activity_echoes_message(agent_app):
    """Test that bot echoes user messages."""
    context = create_mock_context(activity_type="message", text="Hello, bot!")

    await agent_app.on_turn(context)

    # Check that send_activity was called with the echo message
    calls = context.send_activity.call_args_list
    assert len(calls) >= 1

    # Find the echo message (not the typing indicator)
    echo_found = False
    for call in calls:
        arg = call[0][0]
        if isinstance(arg, str) and "Hello, bot!" in arg and "Test User" in arg:
            echo_found = True
            break
    assert echo_found, f"Expected echo message not found in calls: {calls}"


@pytest.mark.asyncio
async def test_on_members_added_sends_welcome(agent_app):
    """Test that bot sends welcome message to new members."""
    member = MagicMock()
    member.id = "new-user-id"

    context = create_mock_context(
        activity_type="conversationUpdate",
        text=None,
        members_added=[member],
    )

    await agent_app.on_turn(context)

    # Check that send_activity was called (may include typing indicator)
    calls = context.send_activity.call_args_list
    assert len(calls) >= 1

    # Find the welcome message
    welcome_found = False
    for call in calls:
        arg = call[0][0]
        if isinstance(arg, str) and "NotebookLM Bot" in arg:
            welcome_found = True
            break
    assert welcome_found, f"Expected welcome message not found in calls: {calls}"
