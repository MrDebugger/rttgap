"""End to end: a real aiohttp server, a real WebSocket client, and on Linux a relay in
the middle that plays the proxy."""
import asyncio
import sys

import aiohttp
import pytest
from aiohttp import web

import rttgap
import rttgap.aiohttp
import rttgap.asgi

LINUX = sys.platform.startswith("linux")


async def echo_client(url):
    """A browser stand-in: echo every probe, return the final message."""
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect(url) as ws:
            async for msg in ws:
                if msg.type != aiohttp.WSMsgType.TEXT:
                    break
                if msg.data.startswith("e"):
                    await ws.send_str(msg.data)
                else:
                    return msg.json()


async def serve(**options):
    results = []
    app = web.Application()
    app.router.add_get("/ws", rttgap.aiohttp.handler(lambda req, r: results.append(r), reveal=True,
                                                     echoes=5, interval=0.01, **options))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    return runner, port, results


def test_aiohttp_with_provided_rtt():
    async def go():
        runner, port, results = await serve(tcp_rtt_ms=0.01)
        try:
            final = await echo_client("http://127.0.0.1:%d/ws" % port)
        finally:
            await runner.cleanup()
        return final, results
    final, results = asyncio.run(go())
    assert final["done"] and final["verdict"] == "direct"
    assert results[0].tcp_source == "provided" and len(results[0].echoes_ms) == 5


def test_aiohttp_refuses_a_local_peer():
    # Connecting from 127.0.0.1 looks exactly like nginx in front: no verdict.
    async def go():
        runner, port, _ = await serve()
        try:
            return await echo_client("http://127.0.0.1:%d/ws" % port)
        finally:
            await runner.cleanup()
    final = asyncio.run(go())
    assert final["verdict"] == "unknown" and "reverse proxy" in final["reason"]


def test_aiohttp_hides_result_unless_revealed():
    async def go():
        app = web.Application()
        app.router.add_get("/ws", rttgap.aiohttp.handler(echoes=2, interval=0.0, tcp_rtt_ms=1.0))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        try:
            return await echo_client("http://127.0.0.1:%d/ws" % site._server.sockets[0].getsockname()[1])
        finally:
            await runner.cleanup()
    assert asyncio.run(go()) == {"done": True}


@pytest.mark.skipif(not LINUX, reason="reads the kernel's tcp_info")
def test_aiohttp_direct_reads_kernel_rtt():
    async def go():
        runner, port, results = await serve(allow_loopback=True)
        try:
            await echo_client("http://127.0.0.1:%d/ws" % port)
        finally:
            await runner.cleanup()
        return results[0]
    r = asyncio.run(go())
    assert r.tcp_source == "kernel-min"
    assert r.verdict == "direct", r


async def relay(listen_port_holder, target_port, delay_to_client):
    """A TCP proxy: it ends the client's connection and opens its own to the server,
    like a residential proxy. Bytes going back to the client are held for
    `delay_to_client` seconds: the hidden leg."""
    async def handle(c_reader, c_writer):
        s_reader, s_writer = await asyncio.open_connection("127.0.0.1", target_port)

        async def pipe(reader, writer, delay):
            try:
                while True:
                    data = await reader.read(65536)
                    if not data:
                        break
                    if delay:
                        await asyncio.sleep(delay)
                    writer.write(data)
                    await writer.drain()
            except (ConnectionError, asyncio.CancelledError):
                pass
            finally:
                writer.close()

        await asyncio.gather(pipe(c_reader, s_writer, 0), pipe(s_reader, c_writer, delay_to_client))

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    listen_port_holder.append(server.sockets[0].getsockname()[1])
    return server


@pytest.mark.skipif(not LINUX, reason="reads the kernel's tcp_info")
def test_aiohttp_through_a_relay_is_proxied():
    async def go():
        runner, port, results = await serve(allow_loopback=True)
        holder = []
        server = await relay(holder, port, delay_to_client=0.06)
        try:
            await echo_client("http://127.0.0.1:%d/ws" % holder[0])
        finally:
            server.close()
            await runner.cleanup()
        return results[0]
    r = asyncio.run(go())
    # The server's TCP peer is the relay (sub-millisecond away); every echo pays 60 ms.
    assert r.tcp_rtt_ms < 5
    assert r.min_echo_ms >= 60
    assert r.verdict == "proxied", r


def test_asgi_with_header():
    from starlette.applications import Starlette
    from starlette.routing import WebSocketRoute
    from starlette.testclient import TestClient

    results = []

    async def endpoint(websocket):
        results.append(await rttgap.asgi.measure(websocket, echoes=4, interval=0.0, reveal=True))

    client = TestClient(Starlette(routes=[WebSocketRoute("/ws", endpoint)]))
    with client.websocket_connect("/ws", headers={"X-TCP-RTT": "150000"}) as ws:   # 150 ms, in microseconds
        while True:
            msg = ws.receive_text()
            if msg.startswith("e"):
                ws.send_text(msg)
            else:
                break
    r = results[0]
    assert r.tcp_rtt_ms == 150.0 and r.tcp_source == "provided"
    assert r.verdict == "direct"     # the in-process echo is far faster than 150 ms


def test_asgi_without_rtt_is_unknown():
    from starlette.applications import Starlette
    from starlette.routing import WebSocketRoute
    from starlette.testclient import TestClient

    results = []

    async def endpoint(websocket):
        results.append(await rttgap.asgi.measure(websocket, echoes=2, interval=0.0))

    client = TestClient(Starlette(routes=[WebSocketRoute("/ws", endpoint)]))
    with client.websocket_connect("/ws") as ws:
        while True:
            msg = ws.receive_text()
            if msg.startswith("e"):
                ws.send_text(msg)
            else:
                break
    assert results[0].verdict == "unknown" and "X-TCP-RTT" in results[0].reason


def test_rtt_from_headers_units():
    assert rttgap.asgi.rtt_from_headers({"X-TCP-RTT": "2500"}) == 2.5
    assert rttgap.asgi.rtt_from_headers({"x-rtt": "7"}, name="x-rtt", unit="ms") == 7.0
    assert rttgap.asgi.rtt_from_headers({"X-TCP-RTT": "abc"}) is None
    assert rttgap.asgi.rtt_from_headers({}) is None


def test_client_js_ships():
    assert "rttgap" in rttgap.CLIENT_JS and "ws.send(m.data)" in rttgap.CLIENT_JS
    assert "</script" not in rttgap.CLIENT_JS.lower()      # safe to inline in a <script> tag
