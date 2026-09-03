"""aiohttp server that streams Telegram video files without storing them locally."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

from aiohttp import web

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from pyrogram import Client
    from pyrogram.types import Message

_CHUNK_SIZE = 1024 * 1024
_HTTP_PARTIAL_CONTENT = 206
_WRITE_TIMEOUT_SECONDS = 15


def create_app(client: Client) -> web.Application:
    """Build the aiohttp application serving the video streaming endpoint.

    Args:
        client: Pyrogram client used to fetch and stream Telegram media.

    Returns:
        Configured aiohttp application.
    """
    app = web.Application()
    app["client"] = client
    app.router.add_get("/stream/{chat_id}/{message_id}/{filename}", _handle_stream)
    return app


async def _handle_stream(request: web.Request) -> web.StreamResponse:
    client: Client = request.app["client"]
    chat_id = int(request.match_info["chat_id"])
    message_id = int(request.match_info["message_id"])

    message = await client.get_messages(chat_id, message_id)
    if message is None:
        raise web.HTTPNotFound(text="Video not found")
    media = message.video or message.document
    if media is None or media.file_size is None:
        raise web.HTTPNotFound(text="Video not found")

    file_size = media.file_size
    mime_type = media.mime_type or "video/mp4"
    start, end, status = _parse_range(request.headers.get("Range"), file_size)

    response = web.StreamResponse(status=status)
    response.headers["Content-Type"] = mime_type
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Content-Length"] = str(end - start + 1)
    if status == _HTTP_PARTIAL_CONTENT:
        response.headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
    await response.prepare(request)

    await _write_range(client, message, start, end, response)
    await response.write_eof()
    return response


def _parse_range(range_header: str | None, file_size: int) -> tuple[int, int, int]:
    if not range_header:
        return 0, file_size - 1, 200

    range_value = range_header.removeprefix("bytes=")
    start_str, _, end_str = range_value.partition("-")
    start = int(start_str) if start_str else 0
    end = int(end_str) if end_str else file_size - 1
    return start, min(end, file_size - 1), _HTTP_PARTIAL_CONTENT


async def _write_range(
    client: Client,
    message: Message,
    start: int,
    end: int,
    response: web.StreamResponse,
) -> None:
    offset_chunks = start // _CHUNK_SIZE
    skip = start % _CHUNK_SIZE
    remaining = end - start + 1

    # stream_media is implemented as an async generator (it uses yield) even though
    # its declared return type is the narrower AsyncIterator, which lacks aclose().
    media_stream = cast("AsyncGenerator[bytes]", client.stream_media(message, offset=offset_chunks))
    try:
        async for raw_chunk in media_stream:
            chunk = raw_chunk[skip:] if skip else raw_chunk
            skip = 0
            if len(chunk) > remaining:
                chunk = chunk[:remaining]
            try:
                await asyncio.wait_for(response.write(chunk), timeout=_WRITE_TIMEOUT_SECONDS)
            except (ConnectionResetError, ConnectionError, TimeoutError):
                return
            remaining -= len(chunk)
            if remaining <= 0:
                return
    finally:
        # A seek in the player abandons this request mid-stream (disconnect or
        # task cancellation); without an explicit aclose() the semaphore inside
        # stream_media stays held until garbage collection, freezing the next
        # request since Client.max_concurrent_transmissions caps concurrency.
        await media_stream.aclose()
