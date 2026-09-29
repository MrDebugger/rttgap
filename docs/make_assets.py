"""Render the README and social images from HTML (needs: pip install playwright).

    python docs/make_assets.py

Writes docs/assets/{logo.png, how-it-works.png, social-preview.png}.
"""
import pathlib

from playwright.sync_api import sync_playwright

ASSETS = pathlib.Path(__file__).parent / "assets"
LOGO = (ASSETS / "logo.svg").read_text(encoding="utf-8")

BASE = """<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700;800&display=swap" rel="stylesheet">
<style>
 :root{--bg:#0D0D0E;--ink:#E8E8E8;--ink2:#8A8A8D;--ink3:#5A5A5D;--g:#00FFA3;--a:#FFB800;--r:#FF3131;--line:#2A2A2D}
 *{box-sizing:border-box;margin:0} html,body{width:%dpx;height:%dpx;overflow:hidden}
 body{background:var(--bg);color:var(--ink);font-family:'JetBrains Mono',monospace;
      background-image:radial-gradient(#1c1c1f 1.5px,transparent 1.5px);background-size:32px 32px}
</style></head><body>%s</body></html>"""

# Direct vs proxied, side by side: what each clock measures.
HOW = """
<style>
 .wrap{padding:56px 64px}
 h1{font-size:34px;font-weight:700} h1 span{color:var(--g)}
 .sub{color:var(--ink2);font-size:19px;margin-top:10px}
 .rows{display:grid;gap:30px;margin-top:40px}
 .row{border:1px solid var(--line);border-radius:18px;padding:22px 28px;background:rgba(20,20,22,.8);display:grid;grid-template-columns:1fr 250px;align-items:center}
 .tag{font-size:15px;letter-spacing:.18em;color:var(--ink2)}
 .res{text-align:right} .res .gap{font-size:36px;font-weight:800} .res .v{font-size:16px;letter-spacing:.14em;margin-top:4px}
 .nums{font-size:17px;color:var(--ink2);margin-top:6px}
 svg text{font-family:'JetBrains Mono',monospace}
</style>
<div class="wrap">
 <h1>The proxy ends TCP. The echo <span>keeps going.</span></h1>
 <div class="sub">The kernel times the TCP round trip. The page times an echo. Direct, they match. Through a proxy, the echo pays the hidden leg.</div>
 <div class="rows">
  <div class="row">
   <div>
    <div class="tag">DIRECT</div>
    <svg width="100%" viewBox="0 0 1000 190">
     <path d="M170 95 H840" stroke="#2A2A2D" stroke-width="3" stroke-dasharray="6 8"/>
     <circle cx="150" cy="95" r="18" fill="#E8E8E8"/><text x="120" y="101" fill="#8A8A8D" font-size="17" text-anchor="end">browser</text>
     <circle cx="860" cy="95" r="18" fill="#00FFA3"/><text x="890" y="101" fill="#8A8A8D" font-size="17">server</text>
     <path d="M842 80 Q505 0 168 80" stroke="#00FFA3" stroke-width="4" fill="none"/><text x="505" y="24" fill="#00FFA3" font-size="17" text-anchor="middle">TCP round trip 40 ms</text>
     <path d="M842 110 Q505 190 168 110" stroke="#FFB800" stroke-width="4" fill="none"/><text x="505" y="178" fill="#FFB800" font-size="17" text-anchor="middle">echo 41 ms</text>
    </svg>
   </div>
   <div class="res"><div class="gap" style="color:var(--g)">+1 ms</div><div class="v" style="color:var(--g)">DIRECT</div></div>
  </div>
  <div class="row">
   <div>
    <div class="tag">THROUGH A RESIDENTIAL PROXY</div>
    <svg width="100%" viewBox="0 0 1000 190">
     <path d="M170 95 H840" stroke="#2A2A2D" stroke-width="3" stroke-dasharray="6 8"/>
     <circle cx="150" cy="95" r="18" fill="#E8E8E8"/><text x="120" y="101" fill="#8A8A8D" font-size="17" text-anchor="end">browser</text>
     <rect x="640" y="75" width="44" height="40" rx="9" fill="#FFB800"/><text x="662" y="62" fill="#FFB800" font-size="17" text-anchor="middle">proxy</text>
     <circle cx="860" cy="95" r="18" fill="#00FFA3"/><text x="890" y="101" fill="#8A8A8D" font-size="17">server</text>
     <path d="M842 80 Q766 30 690 80" stroke="#00FFA3" stroke-width="4" fill="none"/><text x="766" y="40" fill="#00FFA3" font-size="17" text-anchor="middle">TCP 2 ms</text>
     <path d="M842 110 Q505 190 168 110" stroke="#FFB800" stroke-width="4" fill="none"/><text x="505" y="178" fill="#FFB800" font-size="17" text-anchor="middle">echo 176 ms</text>
     <text x="400" y="82" fill="#5A5A5D" font-size="15" text-anchor="middle">hidden leg</text>
    </svg>
   </div>
   <div class="res"><div class="gap" style="color:var(--r)">+174 ms</div><div class="v" style="color:var(--r)">PROXIED</div></div>
  </div>
 </div>
</div>"""

SOCIAL = """
<style>
 .wrap{position:absolute;inset:0;padding:70px 80px;display:grid;grid-template-columns:230px 1fr;gap:56px;align-items:center}
 .glow{position:absolute;inset:0;background:radial-gradient(circle at 20%% 45%%,rgba(0,255,163,.10),transparent 55%%)}
 .logo svg{width:230px;height:230px;display:block}
 .name{font-size:96px;font-weight:800;letter-spacing:-.02em}
 .tag{font-size:27px;color:var(--ink2);margin-top:10px;line-height:1.4}
 .stats{display:flex;gap:16px;margin-top:34px;flex-wrap:wrap}
 .s{border:1px solid var(--line);border-radius:14px;padding:12px 18px;background:rgba(20,20,22,.8)}
 .s b{display:block;font-size:30px} .s span{font-size:15px;color:var(--ink2)}
 .pip{margin-top:28px;font-size:24px;color:var(--g)} .pip i{color:var(--ink3);font-style:normal}
 .foot{position:absolute;left:80px;right:80px;bottom:38px;display:flex;justify-content:space-between;font-size:18px;color:var(--ink3)}
 .foot b{color:var(--g);font-weight:500}
</style>
<div class="glow"></div>
<div class="wrap">
 <div class="logo">%s</div>
 <div>
  <div class="name">rttgap</div>
  <div class="tag">Spot proxied visitors from the gap between<br>the TCP round trip and a WebSocket echo.</div>
  <div class="stats">
   <div class="s"><b style="color:var(--g)">798/798</b><span>residential proxy sessions caught</span></div>
   <div class="s"><b>0/50</b><span>direct visits flagged</span></div>
  </div>
  <div class="pip"><i>$</i> pip install rttgap</div>
 </div>
</div>
<div class="foot"><span>github.com/MrDebugger/rttgap</span><span><b>ijazurrahim.com</b></span></div>"""


def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        jobs = [
            ("logo.png", 512, 512, '<div style="padding:0">%s</div>' % LOGO.replace("<svg ", '<svg width="512" height="512" '), 1),
            ("how-it-works.png", 1400, 780, HOW, 1.5),
            ("social-preview.png", 1280, 640, SOCIAL % LOGO, 1),
        ]
        for name, w, h, body, scale in jobs:
            page = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=scale)
            page.set_content(BASE % (w, h, body))
            page.wait_for_load_state("networkidle")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(300)
            if name == "logo.png":
                page.locator("svg").screenshot(path=str(ASSETS / name), omit_background=True)
            else:
                page.screenshot(path=str(ASSETS / name))
            page.close()
            print("wrote", name)
        b.close()


if __name__ == "__main__":
    main()
