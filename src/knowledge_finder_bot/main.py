"""Application entrypoint - aiohttp server with M365 Agents SDK."""

import logging

import structlog
from aiohttp.web import Request, Response, Application, run_app
from microsoft_agents.hosting.aiohttp import (
    CloudAdapter,
    start_agent_process,
)
from microsoft_agents.hosting.core import AgentApplication

from knowledge_finder_bot.acl.service import ACLService
from knowledge_finder_bot.auth.graph_client import GraphClient
from knowledge_finder_bot.bot import create_agent_app
from knowledge_finder_bot.config import get_settings


def configure_logging(
    log_level: str = "INFO",
    log_file: str = "",
    log_file_max_bytes: int = 10_485_760,
    log_file_backup_count: int = 5,
) -> None:
    """Configure structlog and standard library logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file. Empty string = console only.
        log_file_max_bytes: Max size per log file before rotation (default: 10 MB)
        log_file_backup_count: Number of rotated backup files to keep (default: 5)
    """
    from logging.handlers import RotatingFileHandler
    from pathlib import Path
    
    # Determine log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.root
    root_logger.setLevel(level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Always add console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(console_handler)
    
    # Conditionally add file handler with rotation
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=log_file_max_bytes,
            backupCount=log_file_backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(file_handler)
    
    # Configure structlog processors
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            # Use JSONRenderer for file, ConsoleRenderer for console
            structlog.processors.JSONRenderer() if log_file else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()


async def messages(request: Request) -> Response:
    agent: AgentApplication = request.app["agent_app"]
    adapter: CloudAdapter = request.app["adapter"]
    response = await start_agent_process(request, agent, adapter)
    return response if response is not None else Response(status=202)


async def health(request: Request) -> Response:
    """Health check endpoint - no authentication required."""
    from aiohttp import web
    return web.json_response({"status": "healthy"})


async def messages_health(request: Request) -> Response:
    return Response(status=200)


def create_app() -> Application:
    """Create and configure the aiohttp application."""
    settings = get_settings()

    # Initialize ACL components (optional — graceful fallback to echo mode)
    graph_client = None
    mock_client = None
    acl_service = None

    try:
        # Always try to create the real Graph API client
        graph_client = GraphClient(
            client_id=settings.graph_client_id,
            client_secret=settings.graph_client_secret,
            tenant_id=settings.app_tenant_id,
        )
        logger.info("graph_client_initialized", mode="real")
    except Exception as e:
        logger.warning("graph_client_disabled", reason=str(e))

    # In test mode, also create mock client for Agent Playground fake AAD IDs
    if settings.test_mode:
        from knowledge_finder_bot.auth.mock_graph_client import MockGraphClient
        test_groups = [g.strip() for g in settings.test_user_groups.split(",") if g.strip()]
        mock_client = MockGraphClient(test_groups)
        logger.info("dual_mode_enabled", test_groups=test_groups)

    try:
        acl_service = ACLService(settings.acl_config_path)
        logger.info("acl_service_loaded", config_path=settings.acl_config_path)
    except Exception as e:
        logger.warning("acl_disabled", reason=str(e))

    # Initialize nlm-proxy client (optional — graceful fallback to echo mode)
    nlm_client = None
    if settings.nlm_proxy_url and settings.nlm_proxy_api_key:
        from knowledge_finder_bot.nlm import NLMClient
        from knowledge_finder_bot.nlm.memory import ConversationMemoryManager
        memory = ConversationMemoryManager(
            ttl=settings.nlm_memory_ttl,
            maxsize=settings.nlm_memory_maxsize,
            max_messages=settings.nlm_memory_max_messages,
        )
        nlm_client = NLMClient(
            settings,
            memory=memory,
            enable_rewrite=settings.nlm_enable_rewrite,
            enable_followup=settings.nlm_enable_followup,
        )
        logger.info("nlm_client_initialized", url=settings.nlm_proxy_url)
    else:
        logger.info("nlm_client_disabled", reason="NLM_PROXY_URL or NLM_PROXY_API_KEY not set")

    agent_app = create_agent_app(
        settings=settings,
        graph_client=graph_client,
        acl_service=acl_service,
        mock_graph_client=mock_client,
        nlm_client=nlm_client,
    )

    app = Application()
    app["agent_configuration"] = agent_app._connection_manager.get_default_connection_configuration()
    app["agent_app"] = agent_app
    app["adapter"] = agent_app.adapter

    app.router.add_post("/api/messages", messages)
    app.router.add_get("/api/messages", messages_health)
    app.router.add_get("/health", health)

    return app


def main() -> None:
    """Run the bot server."""
    settings = get_settings()
    configure_logging(
        log_level=settings.log_level,
        log_file=settings.log_file,
        log_file_max_bytes=settings.log_file_max_bytes,
        log_file_backup_count=settings.log_file_backup_count,
    )

    logger.info(
        "starting_bot_server",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )

    app = create_app()
    run_app(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
