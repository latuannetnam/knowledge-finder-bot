"""Application entrypoint - aiohttp server with M365 Agents SDK."""

import sys

import structlog
from aiohttp import web
from microsoft_agents.hosting.aiohttp import CloudAdapter

from knowledge_finder_bot.bot import create_agent_app
from knowledge_finder_bot.config import get_settings

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


async def messages(request: web.Request) -> web.Response:
    """Handle incoming Bot Framework messages.

    Args:
        request: The incoming HTTP request from Bot Framework

    Returns:
        HTTP response from CloudAdapter
    """
    adapter: CloudAdapter = request.app["adapter"]
    agent_app = request.app["agent_app"]

    try:
        response = await adapter.process(request, agent_app)
        return response or web.Response(status=200)
    except Exception as e:
        logger.exception("Error processing activity", error=str(e))
        return web.Response(status=500)


async def health(request: web.Request) -> web.Response:
    """Health check endpoint.

    Args:
        request: The incoming HTTP request

    Returns:
        JSON response with health status
    """
    return web.json_response({"status": "healthy"})


def create_app() -> web.Application:
    """Create and configure the aiohttp application.

    Returns:
        Configured aiohttp Application
    """
    settings = get_settings()

    # Create M365 Agents SDK adapter
    adapter = CloudAdapter()

    # Create agent application
    agent_app = create_agent_app(settings)

    # Create aiohttp app
    app = web.Application()
    app["adapter"] = adapter
    app["agent_app"] = agent_app
    app["settings"] = settings

    # Add routes
    app.router.add_post("/api/messages", messages)
    app.router.add_get("/health", health)

    return app


def main() -> None:
    """Run the bot server."""
    settings = get_settings()

    logger.info(
        "starting_bot_server",
        host=settings.host,
        port=settings.port,
    )

    app = create_app()
    web.run_app(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
