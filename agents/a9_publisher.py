"""A9 Publisher -- runs 08:30 daily, AFTER the 08:00 human review window
(master plan section 5.4). It never decides what's good -- it only flips
drafts that a human already approved into "publish", then would ping
Google/social/FCM (section 5.4). News & Sarkari stay human-gated per the
permanent trust rule in section 7.1 -- this script intentionally never
auto-approves anything.

Phase 0 site is Astro (not WordPress -- see master plan section 4 update).
"Publishing" means writing the approved draft straight into the site's
content collection (site/src/content/articles/) plus its image into
site/public/images/ -- the next `astro build` picks it up statically.
"""

import argparse
import json
import shutil
from datetime import datetime, timezone

from lib import dedup
from lib.config import DRAFTS_DIR, SITE_CONTENT_DIR, SITE_IMAGES_DIR
from lib.logger import get_logger

log = get_logger("A9_publisher")


def list_pending() -> list[dict]:
    """Drafts waiting for human approval in data/drafts/."""
    items = []
    for path in sorted(DRAFTS_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        items.append({"source": "local", "path": str(path), **data})
    return items


def publish_to_site(slug: str) -> None:
    """Human has approved this draft -- write it into the Astro content
    collection and copy its image into public/. This is the only path that
    makes a draft visible on the live site; nothing else does this."""
    draft_path = DRAFTS_DIR / f"{slug}.json"
    if not draft_path.exists():
        raise FileNotFoundError(f"No local draft found for slug={slug!r}")

    data = json.loads(draft_path.read_text())
    image_src = DRAFTS_DIR / f"{slug}.png"

    SITE_CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    SITE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    site_entry = {
        "title": data["title"],
        "slug": data["slug"],
        "meta_description": data["excerpt"],
        "html_body": data["html_body"],
        "faq": data.get("faq", []),
        "tags": data.get("tags", []),
        "category": data.get("category", "News"),
        "fact_sources": data.get("fact_sources", []),
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    if image_src.exists():
        shutil.copy(image_src, SITE_IMAGES_DIR / f"{slug}.png")
        site_entry["image"] = f"/images/{slug}.png"

    (SITE_CONTENT_DIR / f"{slug}.json").write_text(
        json.dumps(site_entry, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info("Published to site content collection: %s", slug)


def run_list() -> None:
    started_at = datetime.now(timezone.utc).isoformat()
    pending = list_pending()
    if not pending:
        log.info("No drafts waiting for review.")
    for item in pending:
        log.info("PENDING REVIEW: [%s] %s -- %s", item.get("status"), item.get("title"), item.get("path"))
    dedup.log_run("A9", "success", f"pending_reviewed={len(pending)}", started_at)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A9 Publisher")
    parser.add_argument("--list", action="store_true", help="list drafts awaiting human review")
    parser.add_argument("--publish", metavar="SLUG", help="human-approved: publish this draft to the live site")
    args = parser.parse_args()

    if args.publish:
        publish_to_site(args.publish)
    else:
        run_list()
