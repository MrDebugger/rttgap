"""rttgap: spot proxied visitors by comparing the TCP round trip with a WebSocket echo.

A residential, corporate or relay proxy ends the visitor's TCP connection early. The
kernel's round trip stops at the proxy; an echo sent to the page travels on to the real
browser. The difference is the part of the path the proxy hides.

    import rttgap
    rttgap.evaluate(tcp_rtt_ms=2.1, echoes_ms=[176.0, 174.2, 180.9]).verdict   # "proxied"

Integrations: rttgap.aiohttp (reads tcp_info from the socket) and rttgap.asgi
(Starlette / FastAPI behind nginx). Browser side: rttgap.CLIENT_JS.
"""
from importlib import resources as _resources

from .core import DEFAULT, Result, Thresholds, evaluate
from .measure import result_for, run_echoes
from .tcpinfo import TcpInfo, is_loopback_peer
from .tcpinfo import read as read_tcp_info

__version__ = "0.1.0"
__all__ = ["DEFAULT", "Result", "Thresholds", "evaluate", "result_for", "run_echoes",
           "TcpInfo", "read_tcp_info", "is_loopback_peer", "CLIENT_JS", "__version__"]

#: The browser snippet, to serve as a static file or inline in a page.
CLIENT_JS: str = _resources.files(__package__).joinpath("client.js").read_text(encoding="utf-8")
