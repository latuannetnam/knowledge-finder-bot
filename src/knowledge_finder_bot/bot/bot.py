"""Bot handler with ACL enforcement using M365 Agents SDK."""

import re
import traceback

import structlog
from cachetools import TTLCache
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
from microsoft_agents.activity import ConversationUpdateTypes, load_configuration_from_env

from knowledge_finder_bot.acl.service import ACLService
from knowledge_finder_bot.auth.graph_client import GraphClient, UserInfo
from knowledge_finder_bot.config import Settings

logger = structlog.get_logger()


def create_agent_app(
    settings: Settings,
    graph_client: GraphClient | None = None,
    acl_service: ACLService | None = None,
) -> AgentApplication[TurnState]:
    """Create and configure the agent application with ACL support.

    Args:
        settings: Application settings.
        graph_client: Graph API client (None disables ACL, echo-only mode).
        acl_service: ACL service (None disables ACL, echo-only mode).
    """
    load_dotenv()

    agents_sdk_config = load_configuration_from_env(dict(environ))

    storage = MemoryStorage()
    connection_manager = MsalConnectionManager(**agents_sdk_config)
    adapter = CloudAdapter(connection_manager=connection_manager)
    authorization = Authorization(storage, connection_manager, **agents_sdk_config)

    agent_app = AgentApplication[TurnState](
        storage=storage,
        adapter=adapter,
        authorization=authorization,
        **agents_sdk_config,
    )

    # Store connection manager for main.py access
    agent_app._connection_manager = connection_manager

    # ACL components (None = echo-only mode)
    acl_enabled = graph_client is not None and acl_service is not None
    user_cache: TTLCache | None = None
    if acl_enabled:
        user_cache = TTLCache(
            maxsize=settings.graph_cache_maxsize,
            ttl=settings.graph_cache_ttl,
        )

    @agent_app.conversation_update(ConversationUpdateTypes.MEMBERS_ADDED)
    async def on_members_added(context: TurnContext, state: TurnState):
        for member in context.activity.members_added or []:
            if member.id != context.activity.recipient.id:
                await context.send_activity(
                    "Hello! I'm the NotebookLM Bot.\n\n"
                    "Ask me anything about your organization's knowledge bases."
                )

    @agent_app.message(re.compile(r".*"))
    async def on_message(context: TurnContext, state: TurnState):
        user_message = context.activity.text
        user_name = context.activity.from_property.name or "User"

        if not acl_enabled:
            # Echo-only mode (no Graph/ACL configured)
            logger.info("echo_mode", user_name=user_name)
            await context.send_activity(f"**Echo from {user_name}:** {user_message}")
            return

        # --- ACL-enforced flow ---
        aad_object_id = getattr(context.activity.from_property, "aad_object_id", None)

        if not aad_object_id:
            logger.warning("no_aad_object_id", user_name=user_name)
            await context.send_activity(
                "Unable to identify your account. "
                "Please ensure you're signed into Teams with your work account."
            )
            return

        logger.info(
            "message_received",
            user_name=user_name,
            aad_object_id=aad_object_id,
            message_length=len(user_message or ""),
        )

        # Get user info (cached)
        try:
            if aad_object_id in user_cache:
                user_info = user_cache[aad_object_id]
                logger.debug("user_cache_hit", aad_object_id=aad_object_id)
            else:
                user_info = await graph_client.get_user_with_groups(aad_object_id)
                user_cache[aad_object_id] = user_info
                logger.debug("user_cache_miss", aad_object_id=aad_object_id)
        except Exception as e:
            logger.error("graph_api_failed", error=str(e), aad_object_id=aad_object_id)
            await context.send_activity(
                "Unable to verify your permissions. Please try again later."
            )
            return

        logger.info(
            "user_authenticated",
            user_name=user_info.display_name,
            group_count=len(user_info.groups),
        )

        # Check ACL
        user_group_ids = {g["id"] for g in user_info.groups}
        allowed_notebooks = acl_service.get_allowed_notebooks(user_group_ids)

        if not allowed_notebooks:
            logger.warning(
                "acl_denied",
                user_name=user_info.display_name,
                group_count=len(user_info.groups),
            )
            await context.send_activity(
                "You don't have access to any knowledge bases.\n"
                "Please contact your administrator for access."
            )
            return

        logger.info(
            "acl_granted",
            user_name=user_info.display_name,
            notebook_count=len(allowed_notebooks),
        )

        # Echo with ACL info (nlm-proxy integration comes later)
        notebook_names = [
            acl_service.get_notebook_name(nb_id) or nb_id
            for nb_id in allowed_notebooks
        ]
        notebooks_display = ", ".join(notebook_names)
        await context.send_activity(
            f"**{user_name}:** {user_message}\n\n"
            f"---\n"
            f"*Allowed notebooks: {notebooks_display}*"
        )

    @agent_app.error
    async def on_error(context: TurnContext, error: Exception):
        logger.error("on_turn_error", error=str(error))
        traceback.print_exc()
        await context.send_activity("The bot encountered an error.")

    return agent_app
