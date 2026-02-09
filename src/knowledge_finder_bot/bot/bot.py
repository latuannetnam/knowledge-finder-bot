"""Main bot class - Echo implementation for testing."""

import structlog
from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import Activity, ActivityTypes

from knowledge_finder_bot.config import Settings

logger = structlog.get_logger()


class NotebookLMBot(ActivityHandler):
    """NotebookLM Bot - currently echoes messages for testing.

    This basic implementation verifies Bot Framework integration works
    before adding nlm-proxy and Azure AD functionality.
    """

    def __init__(self, settings: Settings):
        """Initialize bot with settings.

        Args:
            settings: Application configuration
        """
        self.settings = settings

    async def on_message_activity(self, turn_context: TurnContext) -> None:
        """Handle incoming messages by echoing them back.

        Args:
            turn_context: The turn context for this turn of the conversation
        """
        user_message = turn_context.activity.text
        user_name = turn_context.activity.from_property.name or "User"

        logger.info(
            "message_received",
            user_name=user_name,
            message_preview=user_message[:50] if user_message else "",
        )

        # Echo the message back
        echo_text = f"**Echo from {user_name}:** {user_message}"

        await turn_context.send_activity(
            Activity(
                type=ActivityTypes.message,
                text=echo_text,
                text_format="markdown",
            )
        )

    async def on_members_added_activity(
        self,
        members_added: list,
        turn_context: TurnContext,
    ) -> None:
        """Welcome new users to the conversation.

        Args:
            members_added: List of members added to the conversation
            turn_context: The turn context for this turn
        """
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                welcome_text = (
                    "Hello! I'm the NotebookLM Bot.\n\n"
                    "Currently running in **echo mode** for testing.\n"
                    "Send me a message and I'll echo it back!"
                )
                await turn_context.send_activity(welcome_text)
