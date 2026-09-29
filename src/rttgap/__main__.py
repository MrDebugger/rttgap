"""Demo server: python -m rttgap [--host 0.0.0.0] [--port 8080]

Serves a page that runs the check against itself and shows the result. Run it on a
machine visitors reach directly (no nginx or CDN in front), then open it through a
proxy and without one. Needs aiohttp: pip install "rttgap[aiohttp]".
"""
import argparse
import json

from aiohttp import web

import rttgap
import rttgap.aiohttp

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>rttgap demo</title>
<style>body{font:15px/1.6 ui-monospace,monospace;background:#0d0d0e;color:#e8e8e8;max-width:640px;margin:40px auto;padding:0 16px}
b{font-size:28px}.direct{color:#00ffa3}.proxied{color:#ff3131}.unsure,.unknown{color:#ffb800}pre{color:#8a8a8d;white-space:pre-wrap}</style>
</head><body><h1>rttgap</h1><p>TCP round trip vs WebSocket echo.</p><p id="out">Measuring...</p><pre id="raw"></pre>
<script>%s</script>
<script>
rttgap.run('/ws').then(function (r) {
  document.getElementById('out').innerHTML = '<b class="' + r.verdict + '">' + r.verdict + '</b>' +
    (r.gap_ms === null ? '' : ' gap ' + r.gap_ms.toFixed(1) + ' ms');
  document.getElementById('raw').textContent = JSON.stringify(r, null, 2);
}, function (e) { document.getElementById('out').textContent = e.message; });
</script></body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m rttgap", description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--allow-loopback", action="store_true", help="measure local connections too (testing)")
    args = ap.parse_args()

    async def index(_request: web.Request) -> web.Response:
        # "</" would end the inline <script> early
        return web.Response(text=PAGE % rttgap.CLIENT_JS.replace("</", r"<\/"), content_type="text/html")

    def log(request: web.Request, result: rttgap.Result) -> None:
        print(json.dumps({"peer": request.remote, **result.as_dict()}), flush=True)

    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/ws", rttgap.aiohttp.handler(log, reveal=True, allow_loopback=args.allow_loopback))
    web.run_app(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
