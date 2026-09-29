import asyncio

import pytest

from rttgap import result_for, run_echoes


def make_peer(delay_s=0.0, drop_after=None, garbage=False):
    """An in-memory browser: echoes each probe after `delay_s`."""
    inbox: asyncio.Queue = asyncio.Queue()
    sent = []

    async def send(msg):
        sent.append(msg)
        if drop_after is not None and len(sent) > drop_after:
            return
        async def reply():
            await asyncio.sleep(delay_s)
            if garbage:
                await inbox.put("noise")
            await inbox.put(msg)
        asyncio.get_running_loop().create_task(reply())

    async def receive():
        return await inbox.get()

    return send, receive, sent


def test_echoes_measure_the_delay():
    async def go():
        send, receive, sent = make_peer(0.03)
        return await run_echoes(send, receive, count=4, interval=0.0), sent
    echoes, sent = asyncio.run(go())
    assert sent == ["e0", "e1", "e2", "e3"]
    assert len(echoes) == 4 and all(28 <= e < 200 for e in echoes)


def test_other_messages_are_ignored():
    async def go():
        send, receive, _ = make_peer(0.0, garbage=True)
        return await run_echoes(send, receive, count=3, interval=0.0)
    assert len(asyncio.run(go())) == 3


def test_stops_when_peer_goes_quiet():
    async def go():
        send, receive, _ = make_peer(0.0, drop_after=2)
        return await run_echoes(send, receive, count=5, interval=0.0, timeout=0.2)
    assert len(asyncio.run(go())) == 2


def test_stops_when_peer_closes():
    async def go():
        async def send(_):
            pass
        async def receive():
            return None
        return await run_echoes(send, receive, count=5, interval=0.0)
    assert asyncio.run(go()) == []


def test_result_for_provided_rtt():
    r = result_for([150.0, 151.0], tcp_rtt_ms=2.0)
    assert r.verdict == "proxied" and r.tcp_source == "provided"


def test_result_for_without_any_rtt():
    r = result_for([10.0])
    assert r.verdict == "unknown" and "tcp_rtt_ms" in r.reason
