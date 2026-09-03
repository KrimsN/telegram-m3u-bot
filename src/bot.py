"""Pyrogram bot handlers that turn forwarded videos into an m3u playlist."""

from __future__ import annotations

import asyncio
import io
from typing import TYPE_CHECKING

from pyrogram import filters

if TYPE_CHECKING:
    from pyrogram import Client
    from pyrogram.types import Message

    from config import Config

_MEDIA_GROUP_DEBOUNCE_SECONDS = 1.5

_pending_groups: dict[int, list[Message]] = {}
_pending_group_tasks: dict[int, asyncio.Task] = {}


def register_handlers(client: Client, config: Config) -> None:
    """Register message handlers that build and send m3u playlists.

    Args:
        client: Pyrogram client to attach handlers to.
        config: Runtime configuration, used for the public streaming base URL.
    """

    @client.on_message(filters.video | filters.document)
    async def handle_video_message(client: Client, message: Message) -> None:
        chat_id = message.chat.id if message.chat else None
        if chat_id is None or not _is_video_message(message):
            return

        if message.media_group_id is not None:
            await _buffer_media_group(client, message, config.public_base_url)
            return

        await _send_playlist(client, chat_id, [message], config.public_base_url)


def _is_video_message(message: Message) -> bool:
    if message.video is not None:
        return True
    mime_type = message.document.mime_type if message.document else None
    return bool(mime_type and mime_type.startswith("video/"))


async def _buffer_media_group(client: Client, message: Message, base_url: str) -> None:
    group_id = message.media_group_id
    if group_id is None:
        return

    _pending_groups.setdefault(group_id, []).append(message)

    existing_task = _pending_group_tasks.get(group_id)
    if existing_task:
        existing_task.cancel()
    _pending_group_tasks[group_id] = asyncio.create_task(_flush_media_group(client, group_id, base_url))


async def _flush_media_group(client: Client, media_group_id: int, base_url: str) -> None:
    await asyncio.sleep(_MEDIA_GROUP_DEBOUNCE_SECONDS)
    messages = _pending_groups.pop(media_group_id, [])
    _pending_group_tasks.pop(media_group_id, None)
    first_chat_id = messages[0].chat.id if messages and messages[0].chat else None
    if first_chat_id is not None:
        await _send_playlist(client, first_chat_id, messages, base_url)


def _build_playlist(messages: list[Message], base_url: str) -> str:
    lines = ["#EXTM3U"]
    for message in messages:
        media = message.video or message.document
        if media is None or message.chat is None:
            continue
        file_name = media.file_name or f"{message.id}.mp4"
        lines.append(f"#EXTINF:-1,{file_name}")
        lines.append(f"{base_url}/stream/{message.chat.id}/{message.id}/{file_name}")
    return "\n".join(lines) + "\n"


async def _send_playlist(
    client: Client,
    chat_id: int,
    messages: list[Message],
    base_url: str,
) -> None:
    playlist = _build_playlist(messages, base_url)
    playlist_file = io.BytesIO(playlist.encode("utf-8"))
    playlist_file.name = "playlist.m3u"
    await client.send_document(chat_id, playlist_file)
