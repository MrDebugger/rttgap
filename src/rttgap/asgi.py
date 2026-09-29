"""Starlette / FastAPI integration.

ASGI servers don't expose the TCP socket, so the round trip has to come from whatever
terminates TCP in front of the app. With nginx:

    location /rttgap {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header X-TCP-RTT $tcpinfo_rtt;     # microseconds
    }

    from fastapi import FastAPI, WebSocket
    import rttgap.asgi

    app = FastAPI()

    @app.websocket("/rttgap")
    async def gap(websocket: WebSocket):
        result = await rttgap.asgi.measure(websocket)
        ...   # result.verdict: "direct" | "unsure" | "proxied" | "unknown"

nginx's $tcpinfo_rtt is a smoothed RTT sampled when the request arrives. It runs high
on congested links, which shrinks the gap: expect a few proxied sessions to read as
"unsure". Only trust X-TCP-RTT from your own proxy; strip it from client requests.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Mapping, Optional, Union

from .core import DEFAULT, Number, Result, Thresholds, evaluate
from .measure import ECHOES, INTERVAL, TIMEOUT, run_echoes, unknown

RttSource = Union[None, Number, Callable[[], Optional[Number]]]


def rtt_from_headers(headers: Mapping[str, str], name: str = "x-tcp-rtt", unit: str = "us") -> Optional[float]:
    """Read a TCP round trip passed by a reverse proxy. unit: "us" (nginx) or "ms"."""
    raw = None
    for k, v in headers.items():
        if k.lower() == name.lower():
            raw = v
            break
    if raw is None:
        return None
    try:
        value = float(str(raw).strip())
    except ValueError:
        return None
    if value <= 0:
        return None
    return value / 1000 if unit == "us" else value


async def measure(websocket: Any, *, tcp_rtt_ms: RttSource = None, header: str = "x-tcp-rtt",
                  header_unit: str = "us", echoes: int = ECHOES, interval: float = INTERVAL,
                  timeout: float = TIMEOUT, thresholds: Thresholds = DEFAULT,
                  accept: bool = True, reveal: bool = False, close: bool = True) -> Result:
    """Accept the WebSocket, run the echoes, and return the verdict.

    tcp_rtt_ms: a number, or a callable that returns one after the echoes. Defaults to
                the `header` sent by the reverse proxy.
    """
    if accept:
        await websocket.accept()

    async def receive() -> Optional[str]:
        while True:
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                return None
            text = msg.get("text")
            if text is not None:
                return text

    samples = await run_echoes(websocket.send_text, receive, echoes, interval, timeout)
    rtt = tcp_rtt_ms() if callable(tcp_rtt_ms) else tcp_rtt_ms
    if rtt is None:
        rtt = rtt_from_headers(websocket.headers, header, header_unit)
    if rtt is None:
        result = unknown(samples, "no TCP round trip: have the reverse proxy send " + header.upper())
    else:
        result = evaluate(rtt, samples, thresholds, "provided")
    if close:
        try:
            payload = {"done": True}
            if reveal:
                payload.update(result.as_dict())
            await websocket.send_text(json.dumps(payload))
            await websocket.close()
        except Exception:
            pass   # the browser already left
    return result
