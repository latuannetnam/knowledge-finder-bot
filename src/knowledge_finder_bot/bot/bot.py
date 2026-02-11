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
from microsoft_agents.activity import (
    Activity, ConversationUpdateTypes, load_configuration_from_env,
)
from microsoft_agents.hosting.aiohttp.app.streaming.streaming_response import StreamingResponse

from knowledge_finder_bot.acl.service import ACLService
from knowledge_finder_bot.auth.graph_client import GraphClient, UserInfo
from knowledge_finder_bot.config import Settings
from knowledge_finder_bot.nlm.client import NLMClient
from knowledge_finder_bot.nlm.formatter import format_response, format_source_attribution
from knowledge_finder_bot.nlm.session import SessionStore

logger = structlog.get_logger()

# Agent Playground sends fake AAD IDs like 00000000-0000-0000-0000-0000000000020
_FAKE_AAD_PREFIX = "00000000-0000-0000-0000-"


def _is_fake_aad_id(aad_object_id: str) -> bool:
    """Detect fake AAD Object IDs from Agent Playground."""
    return aad_object_id.startswith(_FAKE_AAD_PREFIX)


def create_agent_app(
    settings: Settings,
    graph_client: GraphClient | None = None,
    acl_service: ACLService | None = None,
    mock_graph_client=None,
    nlm_client: NLMClient | None = None,
    session_store: SessionStore | None = None,
) -> AgentApplication[TurnState]:
    """Create and configure the agent application with ACL support.

    Args:
        settings: Application settings.
        graph_client: Real Graph API client (None disables ACL for real users).
        acl_service: ACL service (None disables ACL entirely).
        mock_graph_client: Mock client for Agent Playground fake AAD IDs.
        nlm_client: nlm-proxy client (None falls back to echo mode).
        session_store: Multi-turn session store.
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

    # ACL requires at least one graph client and acl_service
    has_real = graph_client is not None
    has_mock = mock_graph_client is not None
    acl_enabled = (has_real or has_mock) and acl_service is not None
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

        # Pick the right client: fake AAD ID → mock, real AAD ID → Graph API
        is_fake = _is_fake_aad_id(aad_object_id)
        if is_fake and has_mock:
            active_client = mock_graph_client
            source = "mock"
        elif has_real:
            active_client = graph_client
            source = "graph_api"
        elif has_mock:
            active_client = mock_graph_client
            source = "mock"
        else:
            logger.error("no_graph_client_available", aad_object_id=aad_object_id)
            await context.send_activity("Unable to verify your permissions.")
            return

        logger.info(
            "message_received",
            user_name=user_name,
            aad_object_id=aad_object_id,
            message_length=len(user_message or ""),
            source=source,
        )

        # Get user info (cached)
        try:
            if aad_object_id in user_cache:
                user_info = user_cache[aad_object_id]
                logger.debug("user_cache_hit", aad_object_id=aad_object_id)
            else:
                user_info = await active_client.get_user_with_groups(aad_object_id)
                user_cache[aad_object_id] = user_info
                logger.debug("user_cache_miss", aad_object_id=aad_object_id, source=source)
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

        # Query nlm-proxy or fall back to echo
        if nlm_client is None:
            # Echo with ACL info (fallback when nlm-proxy not configured)
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
            return

        # --- nlm-proxy query ---
        streaming = StreamingResponse(context)
        streaming.set_generated_by_ai_label(True)
        use_streaming = streaming._is_streaming_channel

        logger.info(
            "nlm_query_start",
            user_name=user_name,
            use_streaming=use_streaming,
            channel_id=str(getattr(context.activity, "channel_id", None)),
        )

        conversation_id = session_store.get(aad_object_id) if session_store else None
        notebook_id = None
        new_conversation_id = None
        sent_separator = False

        try:
            if use_streaming:
                # Streaming channel (Teams, DirectLine) — use StreamingResponse
                async for chunk in nlm_client.query_stream(
                    user_message=user_message,
                    allowed_notebooks=list(allowed_notebooks),
                    conversation_id=conversation_id,
                ):
                    if chunk.chunk_type == "meta":
                        if chunk.model and notebook_id is None:
                            notebook_id = chunk.model
                            nb_name = acl_service.get_notebook_name(notebook_id)
                            if nb_name:
                                streaming.queue_informative_update(
                                    f"Searching {nb_name}..."
                                )
                        if chunk.conversation_id:
                            new_conversation_id = chunk.conversation_id

                    elif chunk.chunk_type == "reasoning":
                        streaming.queue_text_chunk(chunk.text)

                    elif chunk.chunk_type == "content":
                        if not sent_separator:
                            streaming.queue_text_chunk("\n\n---\n\n")
                            sent_separator = True
                        streaming.queue_text_chunk(chunk.text)

                source_line = format_source_attribution(notebook_id, acl_service)
                if source_line:
                    streaming.queue_text_chunk(source_line)

                await streaming.end_stream()
            else:
                # Non-streaming channel (emulator, webchat) — buffer + send_activity
                await context.send_activity(Activity(type="typing"))

                full_text = ""
                async for chunk in nlm_client.query_stream(
                    user_message=user_message,
                    allowed_notebooks=list(allowed_notebooks),
                    conversation_id=conversation_id,
                ):
                    if chunk.chunk_type == "meta":
                        if chunk.model and notebook_id is None:
                            notebook_id = chunk.model
                        if chunk.conversation_id:
                            new_conversation_id = chunk.conversation_id

                    elif chunk.chunk_type == "reasoning":
                        full_text += chunk.text

                    elif chunk.chunk_type == "content":
                        if not sent_separator:
                            full_text += "\n\n---\n\n"
                            sent_separator = True
                        full_text += chunk.text

                source_line = format_source_attribution(notebook_id, acl_service)
                if source_line:
                    full_text += source_line

                await context.send_activity(full_text)

            if new_conversation_id and session_store:
                session_store.set(aad_object_id, new_conversation_id)

            logger.info(
                "nlm_query_delivered",
                notebook_id=notebook_id,
                conversation_id=new_conversation_id,
                use_streaming=use_streaming,
            )

        except Exception as e:
            logger.error("nlm_query_failed", error=str(e), use_streaming=use_streaming)
            await context.send_activity(
                "I encountered an error. Please try again."
            )

    @agent_app.error
    async def on_error(context: TurnContext, error: Exception):
        logger.error("on_turn_error", error=str(error))
        traceback.print_exc()
        await context.send_activity("The bot encountered an error.")

    return agent_app
