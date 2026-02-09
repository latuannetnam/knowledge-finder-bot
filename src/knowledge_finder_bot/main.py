"""Application entrypoint - aiohttp server with Bot Framework."""

import sys

import structlog
from aiohttp import web
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import Activity

from knowledge_finder_bot.bot import NotebookLMBot
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
        HTTP response (usually empty 200 for Bot Framework)
    """
    if request.content_type != "application/json":
        return web.Response(status=415)

    body = await request.json()
    activity = Activity().deserialize(body)
    auth_header = request.headers.get("Authorization", "")

    adapter: BotFrameworkAdapter = request.app["adapter"]
    bot: NotebookLMBot = request.app["bot"]

    try:
        await adapter.process_activity(activity, auth_header, bot.on_turn)
        return web.Response(status=200)
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

    # Create Bot Framework adapter
    adapter_settings = BotFrameworkAdapterSettings(
        app_id=settings.app_id,
        app_password=settings.app_password,
    )
    adapter = BotFrameworkAdapter(adapter_settings)

    # Create bot
    bot = NotebookLMBot(settings)

    # Create app
    app = web.Application()
    app["adapter"] = adapter
    app["bot"] = bot
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
