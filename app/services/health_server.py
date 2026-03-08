from __future__ import annotations

import asyncio
from contextlib import suppress


HEALTH_RESPONSE = (
    b"HTTP/1.1 200 OK\r\n"
    b"Content-Type: text/plain; charset=utf-8\r\n"
    b"Content-Length: 2\r\n"
    b"Connection: close\r\n"
    b"\r\n"
    b"OK"
)

NOT_FOUND_RESPONSE = (
    b"HTTP/1.1 404 Not Found\r\n"
    b"Content-Type: text/plain; charset=utf-8\r\n"
    b"Content-Length: 9\r\n"
    b"Connection: close\r\n"
    b"\r\n"
    b"Not Found"
)


async def _handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        request_line = await reader.readline()
        path = "/"
        try:
            parts = request_line.decode("utf-8", errors="ignore").strip().split()
            if len(parts) >= 2:
                path = parts[1]
        except Exception:
            path = "/"

        while True:
            line = await reader.readline()
            if not line or line in {b"\r\n", b"\n"}:
                break

        writer.write(HEALTH_RESPONSE if path == "/healthz" else NOT_FOUND_RESPONSE)
        await writer.drain()
    finally:
        writer.close()
        with suppress(Exception):
            await writer.wait_closed()


async def run_health_server(host: str, port: int, stop_event: asyncio.Event) -> None:
    server = await asyncio.start_server(_handle_client, host=host, port=port)
    try:
        await stop_event.wait()
    finally:
        server.close()
        await server.wait_closed()
