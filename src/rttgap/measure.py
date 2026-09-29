"""The echo loop and the step from echoes + a TCP round trip to a Result.

The server sends "e0", "e1", ... over a WebSocket; the browser sends each one straight
back (see rttgap.CLIENT_JS). A text echo is used rather than WebSocket ping frames:
proxies and servers may answer pings themselves, and a page can delay an echo but it
can't answer one early.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable, List, Optional, Union

from .core import DEFAULT, Number, Result, Thresholds, evaluate
from . import tcpinfo

ECHOES = 15
INTERVAL = 0.12      # seconds between probes
TIMEOUT = 5.0        # seconds to wait for one echo

Send = Callable[[str], Awaitable[Any]]
Receive = Callable[[], Awaitable[Optional[str]]]   # None when the socket closed


async def run_echoes(send: Send, receive: Receive, count: int = ECHOES,
                     interval: float = INTERVAL, timeout: float = TIMEOUT) -> List[float]:
    """Send `count` probes, one at a time, and return each round trip in ms.
    Stops early (returning what it has) if the peer closes or goes quiet."""
    echoes: List[float] = []
    for i in range(count):
        token = "e%d" % i
        start = time.perf_counter()
        await send(token)
        while True:
            remaining = start + timeout - time.perf_counter()
            if remaining <= 0:
                return echoes
            try:
                msg = await asyncio.wait_for(receive(), remaining)
            except asyncio.TimeoutError:
                return echoes
            if msg is None:
                return echoes
            if msg == token:
                break
        echoes.append((time.perf_counter() - start) * 1000)
        if i < count - 1:
            await asyncio.sleep(interval)
    return echoes


def unknown(echoes: List[float], reason: str) -> Result:
    return Result("unknown", None, None, round(min(echoes), 3) if echoes else None, echoes, None, reason)


def result_for(echoes: List[float], sock: Any = None,
               tcp_rtt_ms: Union[None, Number, List[Number]] = None,
               thresholds: Thresholds = DEFAULT, allow_loopback: bool = False) -> Result:
    """Pick the TCP round trip (given, or the socket's tcp_info) and evaluate."""
    if tcp_rtt_ms is not None:
        return evaluate(tcp_rtt_ms, echoes, thresholds, "provided")
    if sock is None:
        return unknown(echoes, "no socket and no tcp_rtt_ms")
    if not allow_loopback and tcpinfo.is_loopback_peer(sock):
        return unknown(echoes, "the TCP peer is this machine, so a reverse proxy sits in front: "
                               "pass tcp_rtt_ms from it (nginx: $tcpinfo_rtt)")
    info = tcpinfo.read(sock)
    if info is None:
        return unknown(echoes, "tcp_info is unavailable (Linux only): pass tcp_rtt_ms")
    return evaluate(info.best_ms, echoes, thresholds, info.source)
