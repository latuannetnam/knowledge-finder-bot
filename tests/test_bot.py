"""Tests for bot module."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from knowledge_finder_bot.bot import NotebookLMBot
from knowledge_finder_bot.config import Settings


@pytest.fixture
def bot(settings: Settings) -> NotebookLMBot:
    """Create bot instance for testing."""
    return NotebookLMBot(settings)


@pytest.fixture
def mock_turn_context():
    """Create a mock turn context for testing."""
    context = AsyncMock()
    context.activity = MagicMock()
    context.activity.text = "Hello, bot!"
    context.activity.from_property = MagicMock()
    context.activity.from_property.name = "Test User"
    context.activity.recipient = MagicMock()
    context.activity.recipient.id = "bot-id"
    return context


@pytest.mark.asyncio
async def test_on_message_activity_echoes_message(bot, mock_turn_context):
    """Test that bot echoes user messages."""
    await bot.on_message_activity(mock_turn_context)

    mock_turn_context.send_activity.assert_called_once()
    call_args = mock_turn_context.send_activity.call_args
    activity = call_args[0][0]
    assert "Hello, bot!" in activity.text
    assert "Test User" in activity.text


@pytest.mark.asyncio
async def test_on_members_added_sends_welcome(bot, mock_turn_context):
    """Test that bot sends welcome message to new members."""
    member = MagicMock()
    member.id = "new-user-id"

    await bot.on_members_added_activity([member], mock_turn_context)

    mock_turn_context.send_activity.assert_called_once()
    welcome_text = mock_turn_context.send_activity.call_args[0][0]
    assert "NotebookLM Bot" in welcome_text
