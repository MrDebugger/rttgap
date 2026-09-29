"""aiohttp integration: reads the kernel's minimum RTT straight from the socket.

    from aiohttp import web
    import rttgap.aiohttp

    async def on_result(request, result):
        if result.is_proxied:
            ...   # flag the session

    app = web.Application()
    app.router.add_get("/rttgap", rttgap.aiohttp.handler(on_result))

The page loads rttgap.CLIENT_JS and calls rttgap.run("/rttgap").
Visitors must connect to aiohttp directly. Behind nginx or a CDN, the socket's peer is
the proxy; pass tcp_rtt_ms instead (see rttgap.asgi.rtt_from_headers).
"""
from __future__ import annotations

import inspect
import json
from typing import Any, Awaitable, Callable, Optional, Union

from aiohttp import WSMsgType, web

from .core import DEFAULT, Number, Result, Thresholds
from .measure import ECHOES, INTERVAL, TIMEOUT, result_for, run_echoes

OnResult = Callable[[web.Request, Result], Union[None, Awaitable[None]]]


async def measure(request: web.Request, ws: web.WebSocketResponse, *, echoes: int = ECHOES,
                  interval: float = INTERVAL, timeout: float = TIMEOUT,
                  thresholds: Thresholds = DEFAULT, tcp_rtt_ms: Optional[Number] = None,
                  allow_loopback: bool = False) -> Result:
    """Run the echoes over a prepared WebSocketResponse and return the verdict."""
    transport = request.transport
    sock: Any = transport.get_extra_info("socket") if transport is not None else None

    async def receive() -> Optional[str]:
        while True:
            msg = await ws.receive()
            if msg.type == WSMsgType.TEXT:
                return msg.data
            if msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED, WSMsgType.ERROR):
                return None

    samples = await run_echoes(ws.send_str, receive, echoes, interval, timeout)
    return result_for(samples, sock, tcp_rtt_ms, thresholds, allow_loopback)


def handler(on_result: Optional[OnResult] = None, *, reveal: bool = False, **options: Any):
    """A GET handler that upgrades to a WebSocket, measures, and closes.

    on_result: called with (request, result); may be async.
    reveal:    send the full result to the browser too (demos). By default the browser
               only learns that the measurement finished.
    options:   passed to measure() (echoes, interval, thresholds, tcp_rtt_ms, ...).
    """
    async def _handle(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=None, autoping=True)
        await ws.prepare(request)
        result = await measure(request, ws, **options)
        if on_result is not None:
            out = on_result(request, result)
            if inspect.isawaitable(out):
                await out
        if not ws.closed:
            payload = {"done": True}
            if reveal:
                payload.update(result.as_dict())
            await ws.send_str(json.dumps(payload))
            await ws.close()
        return ws

    return _handle
