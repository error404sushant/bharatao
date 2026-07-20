"""Renders every draft in data/drafts/*.json as a BharatAo-styled HTML page
(using the section 2.1 design tokens) plus an index, then serves them on a
local HTTP server so drafts can be eyeballed in a browser before WordPress
exists (Phase 0 is not done yet)."""

import http.server
import json
import socketserver
import sys
from pathlib import Path

from lib.config import DRAFTS_DIR

PREVIEW_DIR = DRAFTS_DIR / "preview"

TOKENS_CSS = """
:root {
  --ba-saffron: #E8590C; --ba-deep-indigo: #1E2A4A; --ba-peacock: #0F766E;
  --ba-ivory: #FBF7F0; --ba-card: #FFFFFF; --ba-ink: #22243A; --ba-ink-soft: #6B7080;
  --ba-gold: #C9962E; --ba-line: #E8E2D6;
  --font-display: 'Georgia', serif; --font-body: -apple-system, 'Inter', sans-serif;
  --radius-card: 14px; --shadow-card: 0 2px 10px rgba(30,42,74,.07);
}
* { box-sizing: border-box; }
body { background: var(--ba-ivory); color: var(--ba-ink); font-family: var(--font-body);
       max-width: 760px; margin: 0 auto; padding: 32px 20px 80px; line-height: 1.65; }
h1 { font-family: var(--font-display); font-size: 2rem; color: var(--ba-deep-indigo); margin-bottom: 4px; }
.meta { color: var(--ba-ink-soft); font-size: 0.875rem; margin-bottom: 24px; }
.chip { display: inline-block; background: var(--ba-saffron); color: #fff; font-size: 0.75rem;
        padding: 3px 10px; border-radius: 999px; margin-bottom: 12px; }
img.hero { width: 100%; border-radius: var(--radius-card); box-shadow: var(--shadow-card); margin: 16px 0; }
h2 { font-family: var(--font-display); color: var(--ba-deep-indigo); margin-top: 32px; }
.faq { background: var(--ba-card); border: 1px solid var(--ba-line); border-radius: var(--radius-card);
       padding: 16px 20px; margin: 10px 0; }
.faq b { color: var(--ba-deep-indigo); }
.back { display: inline-block; margin-bottom: 20px; color: var(--ba-peacock); text-decoration: none; }
.card { background: var(--ba-card); border: 1px solid var(--ba-line); border-radius: var(--radius-card);
        box-shadow: var(--shadow-card); padding: 20px; margin-bottom: 16px; }
.card a { color: var(--ba-deep-indigo); text-decoration: none; font-weight: 600; font-size: 1.1rem; }
.status { font-size: 0.75rem; color: var(--ba-ink-soft); }
"""


def render_article(data: dict) -> str:
    img_path = f"{data['slug']}.png"
    faq_html = "".join(
        f'<div class="faq"><b>{f["q"]}</b><p>{f["a"]}</p></div>' for f in data.get("faq", [])
    )
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>{data['title']}</title><style>{TOKENS_CSS}</style></head><body>
<a class="back" href="index.html">&larr; All drafts</a>
<span class="chip">News &middot; draft</span>
<h1>{data['title']}</h1>
<p class="meta">{data['excerpt']}</p>
<img class="hero" src="{img_path}" alt="{data['title']}">
{data['html_body']}
<h2>FAQ</h2>
{faq_html}
</body></html>"""


def render_index(articles: list[dict]) -> str:
    cards = "".join(
        f'<div class="card"><a href="{a["slug"]}.html">{a["title"]}</a><br>'
        f'<span class="status">{a.get("status", "draft")} &middot; {len(a.get("faq", []))} FAQ</span></div>'
        for a in articles
    )
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>BharatAo — Draft Queue</title><style>{TOKENS_CSS}</style></head><body>
<h1>BharatAo — Draft Queue</h1>
<p class="meta">Phase 1 local preview &middot; {len(articles)} draft(s) waiting for human review (08:00 window)</p>
{cards or '<p>No drafts yet — run run_phase1.py first.</p>'}
</body></html>"""


def build() -> int:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    articles = []
    for json_path in sorted(DRAFTS_DIR.glob("*.json")):
        data = json.loads(json_path.read_text())
        articles.append(data)
        (PREVIEW_DIR / f"{data['slug']}.html").write_text(render_article(data), encoding="utf-8")
        png_path = DRAFTS_DIR / f"{data['slug']}.png"
        if png_path.exists():
            (PREVIEW_DIR / png_path.name).write_bytes(png_path.read_bytes())
    (PREVIEW_DIR / "index.html").write_text(render_index(articles), encoding="utf-8")
    return len(articles)


def serve(port: int = 8642) -> None:
    n = build()
    print(f"Built preview for {n} draft(s) -> {PREVIEW_DIR}")
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=str(PREVIEW_DIR), **kw)
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Serving at http://127.0.0.1:{port}  (Ctrl+C to stop)")
        httpd.serve_forever()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8642
    serve(port)
