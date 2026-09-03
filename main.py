"""Entry point for telegram-m3u-bot."""

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the bot."""
    logger.info("Hello from telegram-m3u-bot!")


if __name__ == "__main__":
    main()
