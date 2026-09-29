import socket
import struct
import sys

import pytest

from rttgap import tcpinfo


def buffer(rtt_us, min_rtt_us=None, size=232):
    raw = bytearray(size)
    struct.pack_into("=II", raw, 68, rtt_us, 1500)
    if min_rtt_us is not None and size >= 152:
        struct.pack_into("=I", raw, 148, min_rtt_us)
    return bytes(raw)


def test_parse_prefers_min_rtt():
    info = tcpinfo.parse(buffer(24_500, 18_250))
    assert info.rtt_ms == 24.5 and info.rttvar_ms == 1.5 and info.min_rtt_ms == 18.25
    assert info.best_ms == 18.25 and info.source == "kernel-min"


def test_parse_old_kernel_without_min_rtt():
    info = tcpinfo.parse(buffer(24_500, size=104))
    assert info.min_rtt_ms is None
    assert info.best_ms == 24.5 and info.source == "kernel-smoothed"


def test_parse_rejects_short_or_empty():
    assert tcpinfo.parse(b"\x00" * 40) is None
    assert tcpinfo.parse(buffer(0, 0)) is None


def test_read_none_without_socket():
    assert tcpinfo.read(None) is None


def _pair():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    cli = socket.create_connection(srv.getsockname())
    conn, _ = srv.accept()
    return srv, cli, conn


def test_loopback_peer_detected():
    srv, cli, conn = _pair()
    try:
        assert tcpinfo.is_loopback_peer(conn)
    finally:
        for s in (srv, cli, conn):
            s.close()


def test_loopback_false_for_unconnected():
    s = socket.socket()
    try:
        assert not tcpinfo.is_loopback_peer(s)
    finally:
        s.close()


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="tcp_info is Linux-only")
def test_read_live_socket_on_linux():
    srv, cli, conn = _pair()
    try:
        cli.sendall(b"x")
        conn.recv(1)
        info = tcpinfo.read(conn)
        assert info is not None and info.rtt_ms >= 0
        assert info.best_ms < 50            # loopback
    finally:
        for s in (srv, cli, conn):
            s.close()


@pytest.mark.skipif(sys.platform.startswith("linux"), reason="checks the non-Linux fallback")
def test_read_returns_none_off_linux():
    srv, cli, conn = _pair()
    try:
        assert tcpinfo.read(conn) is None
    finally:
        for s in (srv, cli, conn):
            s.close()
