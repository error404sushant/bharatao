import json

from lib.config import DRAFTS_DIR
from lib.logger import get_logger

log = get_logger("draft_store")


def save_draft(title: str, html_body: str, excerpt: str, slug: str, tags: list[str],
                faq: list[dict] | None = None, fact_sources: list[dict] | None = None,
                category: str = "News") -> dict:
    """Writes a drafted article to data/drafts/ for human review (master plan
    5.4: ALWAYS DRAFT FIRST). A9 Publisher --publish is the only thing that
    ever promotes a draft onto the live site."""
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DRAFTS_DIR / f"{slug}.json"
    payload = {
        "title": title,
        "slug": slug,
        "excerpt": excerpt,
        "tags": tags,
        "category": category,
        "status": "draft",
        "html_body": html_body,
        "faq": faq or [],
        "fact_sources": fact_sources or [],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Draft saved: %s", out_path)
    return {"path": str(out_path), "status": "draft"}
