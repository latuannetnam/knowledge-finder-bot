"""Application entrypoint - aiohttp server with M365 Agents SDK."""

import logging
from os import environ

import structlog
from aiohttp.web import Request, Response, Application, run_app
from microsoft_agents.hosting.aiohttp import (
    CloudAdapter,
    start_agent_process,
    jwt_authorization_middleware,
)
from microsoft_agents.hosting.core import AgentApplication

from knowledge_finder_bot.bot import AGENT_APP, CONNECTION_MANAGER
from knowledge_finder_bot.config import get_settings


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog and standard library logging.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Configure Python's standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    # Configure structlog
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
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()


async def messages(request: Request) -> Response:
    """Handle incoming Bot Framework messages."""
    agent: AgentApplication = request.app["agent_app"]
    adapter: CloudAdapter = request.app["adapter"]
    response = await start_agent_process(request, agent, adapter)
    return response if response is not None else Response(status=202)


async def health(request: Request) -> Response:
    """Health check endpoint."""
    from aiohttp import web
    return web.json_response({"status": "healthy"})


async def messages_health(request: Request) -> Response:
    """Health check for messages endpoint."""
    return Response(status=200)


def create_app() -> Application:
    """Create and configure the aiohttp application.

    Returns:
        Configured aiohttp Application
    """
    # Create aiohttp app with JWT authorization middleware
    app = Application(middlewares=[jwt_authorization_middleware])

    # Store components for request handlers (following official MS pattern)
    app["agent_configuration"] = CONNECTION_MANAGER.get_default_connection_configuration()
    app["agent_app"] = AGENT_APP
    app["adapter"] = AGENT_APP.adapter

    # Add routes
    app.router.add_post("/api/messages", messages)
    app.router.add_get("/api/messages", messages_health)
    app.router.add_get("/health", health)

    return app


def main() -> None:
    """Run the bot server."""
    settings = get_settings()

    # Configure logging with level from settings
    configure_logging(settings.log_level)

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
