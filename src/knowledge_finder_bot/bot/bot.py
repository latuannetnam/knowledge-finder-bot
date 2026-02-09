"""Main bot - Echo implementation using M365 Agents SDK."""

import re

import structlog
from microsoft_agents.activity import ConversationUpdateTypes
from microsoft_agents.hosting.core import (
    AgentApplication,
    ApplicationOptions,
    MemoryStorage,
    TurnContext,
    TurnState,
)

from knowledge_finder_bot.config import Settings

logger = structlog.get_logger()


def create_agent_app(settings: Settings) -> AgentApplication[TurnState]:
    """Create and configure the agent application.

    Args:
        settings: Application configuration

    Returns:
        Configured AgentApplication instance
    """
    options = ApplicationOptions(storage=MemoryStorage())
    app: AgentApplication[TurnState] = AgentApplication(options)

    # Store settings for later use
    app.settings = settings  # type: ignore[attr-defined]

    @app.message(re.compile(r".*"))
    async def on_message(context: TurnContext, state: TurnState) -> None:
        """Handle incoming messages by echoing them back."""
        user_message = context.activity.text
        user_name = context.activity.from_property.name or "User"

        logger.info(
            "message_received",
            user_name=user_name,
            message_preview=user_message[:50] if user_message else "",
        )

        # Echo the message back
        echo_text = f"**Echo from {user_name}:** {user_message}"
        await context.send_activity(echo_text)

    @app.conversation_update(ConversationUpdateTypes.MEMBERS_ADDED)
    async def on_members_added(context: TurnContext, state: TurnState) -> None:
        """Welcome new users to the conversation."""
        for member in context.activity.members_added or []:
            if member.id != context.activity.recipient.id:
                welcome_text = (
                    "Hello! I'm the NotebookLM Bot.\n\n"
                    "Currently running in **echo mode** for testing.\n"
                    "Send me a message and I'll echo it back!"
                )
                await context.send_activity(welcome_text)

    return app
