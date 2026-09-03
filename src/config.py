"""Environment-based configuration for the bot and streaming server."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Runtime configuration loaded from environment variables."""

    bot_token: str
    api_id: int
    api_hash: str
    public_base_url: str
    stream_host: str
    stream_port: int


def load_config() -> Config:
    """Load configuration from environment variables.

    Returns:
        Populated `Config` instance.

    Raises:
        ValueError: If a required environment variable is missing.
    """
    return Config(
        bot_token=_require_env("TELEGRAM_BOT_TOKEN"),
        api_id=int(_require_env("TELEGRAM_API_ID")),
        api_hash=_require_env("TELEGRAM_API_HASH"),
        public_base_url=_require_env("PUBLIC_BASE_URL").rstrip("/"),
        stream_host=os.environ.get("STREAM_HOST", "0.0.0.0"),  # noqa: S104
        stream_port=int(os.environ.get("STREAM_PORT", "8080")),
    )


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        message = f"Missing required environment variable: {name}"
        raise ValueError(message)
    return value
