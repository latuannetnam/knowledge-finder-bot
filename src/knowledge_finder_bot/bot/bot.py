"""Main bot - Echo implementation using M365 Agents SDK."""

import re
import sys
import traceback

import structlog
from dotenv import load_dotenv
from os import environ

from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.hosting.core import (
    Authorization,
    AgentApplication,
    TurnState,
    TurnContext,
    MemoryStorage,
)
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.activity import load_configuration_from_env

from knowledge_finder_bot.config import Settings

logger = structlog.get_logger()

# Load environment variables
load_dotenv()

# Load SDK configuration from environment
agents_sdk_config = load_configuration_from_env(environ)

# Create core components following official Microsoft pattern
STORAGE = MemoryStorage()
CONNECTION_MANAGER = MsalConnectionManager(**agents_sdk_config)
ADAPTER = CloudAdapter(connection_manager=CONNECTION_MANAGER)
AUTHORIZATION = Authorization(STORAGE, CONNECTION_MANAGER, **agents_sdk_config)

# Create the agent application
AGENT_APP = AgentApplication[TurnState](
    storage=STORAGE,
    adapter=ADAPTER,
    authorization=AUTHORIZATION,
    **agents_sdk_config
)


@AGENT_APP.conversation_update("membersAdded")
async def on_members_added(context: TurnContext, _state: TurnState):
    """Welcome new users to the conversation."""
    for member in context.activity.members_added or []:
        if member.id != context.activity.recipient.id:
            await context.send_activity(
                "Hello! I'm the NotebookLM Bot.\n\n"
                "Currently running in **echo mode** for testing.\n"
                "Send me a message and I'll echo it back!"
            )
    return True


@AGENT_APP.message(re.compile(r".*"))
async def on_message(context: TurnContext, _state: TurnState):
    """Handle incoming messages by echoing them back."""
    user_message = context.activity.text
    user_name = context.activity.from_property.name or "User"

    logger.info(
        "message_received",
        user_name=user_name,
        message_preview=user_message[:50] if user_message else "",
    )

    echo_text = f"**Echo from {user_name}:** {user_message}"
    await context.send_activity(echo_text)


@AGENT_APP.error
async def on_error(context: TurnContext, error: Exception):
    """Handle errors during message processing."""
    logger.error("on_turn_error", error=str(error))
    traceback.print_exc()
    await context.send_activity("The bot encountered an error.")


def get_agent_app() -> AgentApplication[TurnState]:
    """Get the configured agent application."""
    return AGENT_APP


def get_connection_manager() -> MsalConnectionManager:
    """Get the connection manager for auth configuration."""
    return CONNECTION_MANAGER
