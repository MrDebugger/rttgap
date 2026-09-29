<p align="center">
  <img src="https://raw.githubusercontent.com/MrDebugger/rttgap/main/docs/assets/logo.png" width="128" height="128" alt="rttgap logo">
</p>

<h1 align="center">rttgap</h1>

<p align="center">
  <b>Spot visitors behind residential, corporate and relay proxies<br>from the gap between the TCP round trip and a WebSocket echo.</b>
</p>

<p align="center">
  <a href="https://pypi.org/project/rttgap/"><img src="https://img.shields.io/pypi/v/rttgap?color=00c781&label=pypi" alt="PyPI"></a>
  <a href="https://pypi.org/project/rttgap/"><img src="https://img.shields.io/pypi/pyversions/rttgap" alt="Python versions"></a>
  <a href="https://github.com/MrDebugger/rttgap/actions/workflows/test.yml"><img src="https://github.com/MrDebugger/rttgap/actions/workflows/test.yml/badge.svg" alt="Tests"></a>
  <a href="https://github.com/MrDebugger/rttgap/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT license"></a>
  <a href="https://tools.ijazurrahim.com/proxy-check"><img src="https://img.shields.io/badge/live%20check-try%20it-FFB800" alt="Live check"></a>
</p>

<p align="center">
  <a href="https://tools.ijazurrahim.com/proxy-check">Live check</a> ·
  <a href="https://ijazurrahim.com/blog/residential-proxies-are-detectable.html">Research write-up</a> ·
  <a href="#install">Install</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="#limits">Limits</a>
</p>

---

IP reputation can't see residential proxies: the exits are real home and mobile lines. What a proxy can't hide is the detour.

A proxy ends the visitor's TCP connection and opens its own. Your kernel times the round trip to the proxy. An echo sent to the page travels on to the real browser and back. The difference between the two is the part of the path the proxy hides.

<p align="center">
  <img src="https://raw.githubusercontent.com/MrDebugger/rttgap/main/docs/assets/how-it-works.png" alt="Direct: TCP 40 ms, echo 41 ms, gap +1 ms. Through a residential proxy: TCP 2 ms, echo 176 ms, gap +174 ms." width="100%">
</p>

## Does it work?

I sent 798 browser sessions through residential proxies in 8 countries, plus 50 direct visits, to a server I control.

| Check | Proxied sessions flagged | Direct visits flagged |
|---|---|---|
| Free IP reputation | 7 of 798 | 0 of 50 |
| **rttgap, gap over 25 ms** | **798 of 798** | **0 of 50** |

<p align="center">
  <img src="https://raw.githubusercontent.com/MrDebugger/rttgap/main/docs/assets/results.png" alt="RTT gap per session: every direct visit under 9 ms, every proxied session over 25 ms" width="100%">
</p>

Direct visits landed between 0.3 and 8.5 ms. The closest proxy exit still left 31.5 ms. [Full method and data](https://ijazurrahim.com/blog/residential-proxies-are-detectable.html).

## Install

```bash
pip install "rttgap[aiohttp]"      # reads the kernel's RTT from the socket (Linux)
pip install "rttgap[starlette]"    # FastAPI / Starlette behind nginx
pip install rttgap                 # the verdict only, no dependencies
```

Python 3.9+. The kernel read (`tcp_info`) is Linux-only; everywhere else, pass the round trip in yourself.

## Quick start

### aiohttp

aiohttp exposes the socket, so rttgap reads the kernel's minimum RTT for the connection directly.

```python
from aiohttp import web
import rttgap.aiohttp

async def on_result(request, result):
    if result.is_proxied:
        print("proxied:", request.remote, f"{result.gap_ms:.0f} ms")

app = web.Application()
app.router.add_get("/rttgap", rttgap.aiohttp.handler(on_result))
web.run_app(app)
```

On the page, load the client (serve `rttgap.CLIENT_JS` as a static file, or inline it) and start the measurement:

```html
<script src="/static/rttgap.js"></script>
<script>rttgap.run('/rttgap');</script>
```

The browser only learns that the measurement finished. The verdict stays on your server unless you pass `reveal=True`.

### FastAPI / Starlette

ASGI servers don't expose the socket, so let nginx pass its round trip in a header:

```nginx
location /rttgap {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header X-TCP-RTT $tcpinfo_rtt;   # microseconds
}
```

```python
from fastapi import FastAPI, WebSocket
import rttgap.asgi

app = FastAPI()

@app.websocket("/rttgap")
async def rtt_gap(websocket: WebSocket):
    result = await rttgap.asgi.measure(websocket)
    # result.verdict: "direct" | "unsure" | "proxied" | "unknown"
```

`$tcpinfo_rtt` is a smoothed RTT, sampled when the request arrives. It runs high on congested links, which shrinks the gap, so expect a few proxied sessions to read `unsure`. Only trust `X-TCP-RTT` from your own proxy.

### Just the verdict

```python
import rttgap

r = rttgap.evaluate(tcp_rtt_ms=2.1, echoes_ms=[176.0, 174.2, 180.9])
r.verdict   # "proxied"
r.gap_ms    # 172.1
```

## How it decides

1. The server sends 15 short text messages over a WebSocket, one at a time, and times each echo.
2. It takes the TCP round trip from the kernel (`tcpi_min_rtt`), or from the value you pass.
3. It compares **the fastest echo with the fastest TCP round trip**. A smoothed RTT runs high on congested links, and one lucky sample against many echoes fakes a gap.

| Gap | Verdict | Why |
|---|---|---|
| up to 12 ms | `direct` | the largest direct gap measured was 8.5 ms |
| 12 to 25 ms | `unsure` | busy Wi-Fi or mobile network: measure again |
| over 25 ms | `proxied` | the smallest proxied gap measured was 31.5 ms |
| no data | `unknown` | `result.reason` says why |

Change the limits with `rttgap.Thresholds(proxied=..., unsure=...)`.

A page can delay an echo, but it can't answer one early, so the gap can't be faked away. Text echoes are used instead of WebSocket pings, because proxies and servers may answer pings themselves.

## API

| | |
|---|---|
| `rttgap.evaluate(tcp_rtt_ms, echoes_ms, thresholds=DEFAULT)` | verdict from numbers you already have |
| `rttgap.aiohttp.handler(on_result=None, *, reveal=False, **options)` | ready-made aiohttp WebSocket route |
| `rttgap.aiohttp.measure(request, ws, **options)` | run the echoes over your own `WebSocketResponse` |
| `rttgap.asgi.measure(websocket, *, tcp_rtt_ms=None, header="x-tcp-rtt", ...)` | Starlette / FastAPI |
| `rttgap.read_tcp_info(sock)` | `TcpInfo(rtt_ms, rttvar_ms, min_rtt_ms)` on Linux, else `None` |
| `rttgap.CLIENT_JS` | the browser client, as a string |
| `Result` | `verdict`, `gap_ms`, `tcp_rtt_ms`, `min_echo_ms`, `echoes_ms`, `tcp_source`, `reason`, `is_proxied`, `as_dict()` |

Options: `echoes=15`, `interval=0.12` s between probes, `timeout=5.0` s per echo, `thresholds`, `tcp_rtt_ms`, `allow_loopback=False`.

## Limits

- **VPNs** forward packets instead of ending TCP, so there's no gap to find. Pair rttgap with an IP reputation check.
- **Anything in front of your server** ends the TCP connection first. Behind nginx or a tunnel on the same machine, rttgap returns `unknown` rather than a wrong answer: pass `tcp_rtt_ms` from the proxy. Behind a CDN, measure at the edge instead. On Cloudflare Workers, `request.cf.clientTcpRtt` gives the TCP half, which is how the [live check](https://tools.ijazurrahim.com/proxy-check) works.
- **Mobile networks** speed up and slow down from one second to the next, which can fake a small gap. Treat `unsure`, and gaps just over the threshold, as "measure again on a fresh connection". A real proxy's detour shows up every time.
- **Blocked WebSockets.** Some data-saver modes and corporate proxies cut them. No echoes means `unknown`.

## Demo

```bash
pip install "rttgap[aiohttp]"
python -m rttgap --port 8080
```

Run it on a machine visitors reach directly, then open it with and without a proxy. Each visit's result prints as JSON.

## Contributing

Bug reports, integrations for other frameworks, and data from other proxy networks are all welcome. See [CONTRIBUTING.md](CONTRIBUTING.md). Security issues: [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE) © [Ijaz Ur Rahim](https://ijazurrahim.com)
