# rttgap

Spot visitors behind a residential, corporate or relay proxy by comparing the TCP round trip with a WebSocket echo.

A proxy that ends the TCP connection early can't hide the detour. The kernel's round trip stops at the proxy. An echo sent to the page travels on to the real browser and back. The difference is the hidden leg.

```
direct   browser ──────────────── server     TCP 40 ms   echo 41 ms    gap  +1 ms
proxied  browser ─── proxy ────── server     TCP  2 ms   echo 176 ms   gap +174 ms
```

On 798 residential proxy sessions across 8 countries, a 25 ms threshold flagged all 798, and none of 50 direct visits. IP reputation flagged 7. [Method and data](https://ijazurrahim.com/blog/residential-proxies-are-detectable.html). [Try it on your own connection](https://tools.ijazurrahim.com/proxy-check).

## Install

```
pip install "rttgap[aiohttp]"      # reads tcp_info from the socket (Linux)
pip install "rttgap[starlette]"    # FastAPI / Starlette behind nginx
pip install rttgap                 # just the verdict, no dependencies
```

## aiohttp

aiohttp can read the kernel's minimum RTT for the connection directly, so nothing else is needed.

```python
from aiohttp import web
import rttgap, rttgap.aiohttp

async def on_result(request, result):
    if result.is_proxied:
        print("proxied", request.remote, result.gap_ms)

app = web.Application()
app.router.add_get("/rttgap", rttgap.aiohttp.handler(on_result))
```

On the page, serve `rttgap.CLIENT_JS` and run it:

```html
<script src="/static/rttgap.js"></script>
<script>rttgap.run('/rttgap');</script>
```

The browser only learns that the measurement finished. The verdict stays on the server unless you pass `reveal=True`.

Visitors must reach aiohttp directly. If the TCP peer is the same machine (nginx, Caddy, a tunnel), rttgap returns `unknown` instead of a wrong answer. Pass `tcp_rtt_ms` from the proxy in that case.

## FastAPI / Starlette

ASGI servers don't expose the socket, so let nginx pass its round trip:

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
async def gap(websocket: WebSocket):
    result = await rttgap.asgi.measure(websocket)
    # result.verdict: "direct" | "unsure" | "proxied" | "unknown"
```

`$tcpinfo_rtt` is a smoothed RTT sampled when the request arrives. It runs high on congested links, which shrinks the gap, so expect a few proxied sessions to read `unsure`. Only trust `X-TCP-RTT` from your own proxy.

## Just the verdict

```python
import rttgap

r = rttgap.evaluate(tcp_rtt_ms=2.1, echoes_ms=[176.0, 174.2, 180.9])
r.verdict      # "proxied"
r.gap_ms       # 172.1
```

`tcp_rtt_ms` takes one sample or several. Both sides use their fastest value: a smoothed RTT runs high on congested links, and one lucky sample against many echoes fakes a gap.

## Thresholds

| Gap | Verdict | |
|---|---|---|
| ≤ 12 ms | `direct` | the largest direct gap measured was 8.5 ms |
| 12 to 25 ms | `unsure` | a busy Wi-Fi or mobile network; measure again |
| > 25 ms | `proxied` | the smallest proxied gap measured was 31.5 ms |

Change them with `rttgap.Thresholds(proxied=..., unsure=...)`.

## What it doesn't catch

- **VPNs.** They forward packets instead of ending TCP, so there's no gap. Pair it with an IP reputation check.
- **Anything in front of your server.** Behind a CDN, the TCP connection ends at the CDN. On Cloudflare, use `request.cf.clientTcpRtt` in a Worker instead: that's how the live check works.
- **Noisy mobile links.** Latency moves from second to second, which can fake a small gap. Treat `unsure`, and gaps just over the threshold, as "measure again" rather than "block".

`tcp_info` is read on Linux only. Elsewhere, pass `tcp_rtt_ms` yourself.

## Demo

```
pip install "rttgap[aiohttp]"
python -m rttgap --port 8080
```

Open it directly, then through a proxy.

## License

MIT
