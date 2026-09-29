"""The verdict: compare the fastest TCP round trip with the fastest echo.

A direct visitor's TCP connection and WebSocket echo travel the same path, so the two
round trips match. Through a proxy that ends TCP early (residential, corporate, relay),
the kernel measures the round trip to the proxy, while the echo continues to the real
browser and back. The difference is the hidden leg.

Compare minimum against minimum. A smoothed RTT runs high on congested links, and one
TCP sample against many echoes is lopsided: a lucky low sample makes a fake gap.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Union

Number = Union[int, float]


@dataclass(frozen=True)
class Thresholds:
    """Gap limits in milliseconds. Defaults come from 798 residential proxy sessions
    (smallest gap 31.5 ms) and 50 direct visits (largest gap 8.5 ms)."""

    proxied: float = 25.0
    unsure: float = 12.0

    def __post_init__(self) -> None:
        if self.unsure > self.proxied:
            raise ValueError("unsure threshold must not exceed proxied threshold")


DEFAULT = Thresholds()


@dataclass
class Result:
    verdict: str                          # "direct" | "unsure" | "proxied" | "unknown"
    gap_ms: Optional[float]
    tcp_rtt_ms: Optional[float]
    min_echo_ms: Optional[float]
    echoes_ms: List[float] = field(default_factory=list)
    tcp_source: Optional[str] = None      # "kernel-min", "kernel-smoothed", "provided"
    reason: Optional[str] = None          # why the verdict is "unknown"

    @property
    def is_proxied(self) -> bool:
        return self.verdict == "proxied"

    def as_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "gap_ms": self.gap_ms,
            "tcp_rtt_ms": self.tcp_rtt_ms,
            "min_echo_ms": self.min_echo_ms,
            "echoes_ms": self.echoes_ms,
            "tcp_source": self.tcp_source,
            "reason": self.reason,
        }


def _positive(values: Iterable[Optional[Number]]) -> List[float]:
    out = []
    for v in values:
        if v is None:
            continue
        v = float(v)
        if v > 0 and v == v:          # drop zero, negatives and NaN
            out.append(v)
    return out


def evaluate(
    tcp_rtt_ms: Union[None, Number, Iterable[Optional[Number]]],
    echoes_ms: Iterable[Number],
    thresholds: Thresholds = DEFAULT,
    tcp_source: Optional[str] = None,
) -> Result:
    """Turn TCP round-trip sample(s) and echo round trips into a verdict.

    tcp_rtt_ms: one sample or several; the fastest counts.
    echoes_ms:  application-level echo round trips; the fastest counts.
    """
    samples = [tcp_rtt_ms] if tcp_rtt_ms is None or isinstance(tcp_rtt_ms, (int, float)) else list(tcp_rtt_ms)
    tcp = _positive(samples)
    echoes = _positive(echoes_ms)
    min_echo = round(min(echoes), 3) if echoes else None
    if not echoes:
        return Result("unknown", None, round(min(tcp), 3) if tcp else None, None, echoes, tcp_source, "no echoes")
    if not tcp:
        return Result("unknown", None, None, min_echo, echoes, tcp_source, "no TCP round trip")
    tcp_min = round(min(tcp), 3)
    gap = round(min_echo - tcp_min, 3)
    if gap > thresholds.proxied:
        verdict = "proxied"
    elif gap > thresholds.unsure:
        verdict = "unsure"
    else:
        verdict = "direct"
    return Result(verdict, gap, tcp_min, min_echo, echoes, tcp_source)
