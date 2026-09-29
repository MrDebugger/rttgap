"""Read the kernel's round-trip times for a TCP socket (Linux struct tcp_info).

tcpi_rtt is the smoothed RTT; tcpi_min_rtt (Linux 4.6+) is the lowest RTT the kernel
has seen on the connection, which is what the gap should be measured against.
Returns None on other platforms or when the socket can't be read.
"""
from __future__ import annotations

import ipaddress
import socket
import struct
from dataclasses import dataclass
from typing import Any, Optional

# Offsets into struct tcp_info (include/uapi/linux/tcp.h), values in microseconds
_RTT_OFFSET = 68        # __u32 tcpi_rtt, then tcpi_rttvar
_MIN_RTT_OFFSET = 148   # __u32 tcpi_min_rtt
_READ_SIZE = 232


@dataclass(frozen=True)
class TcpInfo:
    rtt_ms: float           # smoothed
    rttvar_ms: float
    min_rtt_ms: Optional[float]   # None on kernels without tcpi_min_rtt

    @property
    def best_ms(self) -> float:
        """The minimum RTT when the kernel reports it, else the smoothed RTT."""
        return self.min_rtt_ms if self.min_rtt_ms else self.rtt_ms

    @property
    def source(self) -> str:
        return "kernel-min" if self.min_rtt_ms else "kernel-smoothed"


def parse(raw: bytes) -> Optional[TcpInfo]:
    """Parse a raw tcp_info buffer. Exposed for testing."""
    if len(raw) < _RTT_OFFSET + 8:
        return None
    rtt, rttvar = struct.unpack_from("=II", raw, _RTT_OFFSET)
    min_rtt = None
    if len(raw) >= _MIN_RTT_OFFSET + 4:
        (m,) = struct.unpack_from("=I", raw, _MIN_RTT_OFFSET)
        min_rtt = m / 1000 if m else None
    if not rtt and not min_rtt:
        return None
    return TcpInfo(rtt / 1000, rttvar / 1000, min_rtt)


def read(sock: Any) -> Optional[TcpInfo]:
    """tcp_info for a socket (a socket.socket or an asyncio TransportSocket)."""
    opt = getattr(socket, "TCP_INFO", None)
    if sock is None or opt is None:
        return None
    try:
        raw = sock.getsockopt(socket.IPPROTO_TCP, opt, _READ_SIZE)
    except (OSError, ValueError, TypeError):
        return None
    return parse(raw)


def is_loopback_peer(sock: Any) -> bool:
    """True when the socket's peer is this machine: a local reverse proxy (nginx,
    Caddy, a tunnel agent). Its tcp_info then measures the proxy, not the visitor."""
    try:
        host = sock.getpeername()[0]
    except (OSError, AttributeError, IndexError, TypeError):
        return False
    try:
        addr = ipaddress.ip_address(host.split("%")[0])
    except ValueError:
        return False
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return addr.is_loopback
