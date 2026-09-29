/*! rttgap browser client (MIT). Echoes the server's probes back, unchanged.
 *
 * Load this file (or inline rttgap.CLIENT_JS), then call:
 *   rttgap.run('/rttgap').then(function (r) { ... });
 *
 * Resolves when the server says it's done. Unless the server reveals the result,
 * r is just { done: true }: the verdict stays on the server.
 */
(function (root) {
    'use strict';

    function wsUrl(url) {
        if (/^wss?:\/\//.test(url)) return url;
        var loc = root.location;
        var base = (loc.protocol === 'https:' ? 'wss://' : 'ws://') + loc.host;
        return base + (url.charAt(0) === '/' ? url : loc.pathname.replace(/[^/]*$/, '') + url);
    }

    function run(url, opts) {
        opts = opts || {};
        return new Promise(function (resolve, reject) {
            var ws = new WebSocket(wsUrl(url));
            var timer = setTimeout(function () {
                try { ws.close(); } catch (e) {}
                reject(new Error('rttgap: timed out'));
            }, opts.timeout || 15000);
            ws.onmessage = function (m) {
                if (typeof m.data !== 'string') return;
                if (m.data.charAt(0) === 'e') { ws.send(m.data); return; }
                var r;
                try { r = JSON.parse(m.data); } catch (e) { return; }
                if (r && r.done) {
                    clearTimeout(timer);
                    resolve(r);
                    try { ws.close(); } catch (e) {}
                }
            };
            ws.onerror = function () { clearTimeout(timer); reject(new Error('rttgap: WebSocket failed')); };
        });
    }

    root.rttgap = { run: run };
})(typeof window !== 'undefined' ? window : this);
