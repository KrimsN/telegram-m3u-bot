"""Entry point for telegram-m3u-bot."""

import asyncio
import logging

from aiohttp import web
from dotenv import load_dotenv
from pyrogram import Client

from bot import register_handlers
from config import load_config
from streaming import create_app

try:
    import uvloop  # ty: ignore[unresolved-import]
except ImportError:
    uvloop = None

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _run() -> None:
    config = load_config()
    client = Client(
        "telegram-m3u-bot",
        api_id=config.api_id,
        api_hash=config.api_hash,
        bot_token=config.bot_token,
        in_memory=True,
        max_concurrent_transmissions=4,
    )
    register_handlers(client, config)

    app = create_app(client)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.stream_host, config.stream_port)

    await client.start()
    await site.start()
    logger.info("Bot started, streaming on %s:%s", config.stream_host, config.stream_port)

    try:
        await asyncio.Event().wait()
    finally:
        await site.stop()
        await runner.cleanup()
        await client.stop()


def main() -> None:
    """Run the bot and streaming server."""
    if uvloop is not None:
        uvloop.install()
    asyncio.run(_run())


if __name__ == "__main__":
    main()
