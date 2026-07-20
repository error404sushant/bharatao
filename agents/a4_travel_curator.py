"""A4 Travel Curator -- runs Mon & Thu 07:00 (master plan section 5.1).

Season-aware "best places" guide. Evergreen within a season (not RSS-sourced
like A2), so dedup keys on season+year rather than per-day like A6/A7 --
running twice a week during the same season should mean "refresh/vary" not
"duplicate", but we still avoid re-publishing the *exact* same guide twice
in one season without a human noticing.

Images: master plan section 5.3 wants REAL photos (Pexels/Unsplash) for travel,
not AI-generated ones -- "real photos beat AI for places". IMAGE_API_KEY isn't
configured yet, so this falls back to the same honest branded template card
every other pillar uses, rather than faking a photo. Wire in a real Pexels/
Unsplash call here once that key exists.
"""

import requests
from datetime import datetime, timezone

from lib import dedup, draft_store, image_maker
from lib.config import PROMPTS_DIR
from lib.llm_client import chat_completion
from lib.logger import get_logger
from lib.validator import validate_article

log = get_logger("A4_travel_curator")

SYSTEM_PROMPT = (PROMPTS_DIR / "ghumo_v1.md").read_text()

# Simple India-specific season heuristic (master plan 5.2: "season logic").
# A real weather API can refine this later -- these are the broad, stable bands.
SEASONS = {
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Summer", 4: "Summer", 5: "Summer", 6: "Summer",
    7: "Monsoon", 8: "Monsoon", 9: "Monsoon",
    10: "Post-Monsoon/Autumn", 11: "Post-Monsoon/Autumn",
}


def current_season() -> str:
    return SEASONS[datetime.now(timezone.utc).month]


def build_user_prompt(season: str) -> str:
    year = datetime.now(timezone.utc).year
    return f"Current season in India: {season} {year}\n"


def run() -> str:
    """Returns status: 'drafted' | 'needs_human' | 'duplicate'."""
    dedup.init_db()
    season = current_season()
    topic_key = f"Best places to visit - {season} {datetime.now(timezone.utc).year}"

    if dedup.is_duplicate(topic_key):
        log.info("Skip: already published a %s guide recently", season)
        dedup.log_run("A4", "success", "already published this season", datetime.now(timezone.utc).isoformat())
        return "duplicate"

    user_prompt = build_user_prompt(season)
    errors: list[str] = ["agent API never returned a response"]

    for attempt in (1, 2, 3, 4):
        try:
            raw = chat_completion(SYSTEM_PROMPT, user_prompt)
        except (requests.exceptions.RequestException, RuntimeError) as exc:
            errors = [f"agent API call failed: {exc}"]
            log.error("Agent API call failed (attempt %d): %s", attempt, exc)
            continue
        result, article = validate_article(raw)
        errors = result.errors
        if result.ok:
            break
        log.warning("Validation failed (attempt %d): %s", attempt, result.errors)
        user_prompt += f"\n\nPREVIOUS ATTEMPT FAILED VALIDATION: {result.errors}. Fix and resend strict JSON only."
    else:
        dedup.log_run("A4", "needs_human", f"season={season!r} errors={errors}", datetime.now(timezone.utc).isoformat())
        log.error("NEEDS_HUMAN: %s -- %s", season, errors)
        return "needs_human"

    # Fallback branded card (real photo API not configured yet -- see module docstring)
    image_maker.make_branded_card(article["title"], "Ghumo", article["slug"])
    draft = draft_store.save_draft(
        title=article["title"],
        html_body=article["html_body"],
        excerpt=article["meta_description"],
        slug=article["slug"],
        tags=article.get("tags", []),
        faq=article.get("faq", []),
        fact_sources=article.get("fact_sources", []),
        category="Ghumo",
    )

    dedup.mark_published(topic_key, "Ghumo")
    dedup.log_run("A4", "success", f"season={season!r} draft={draft}", datetime.now(timezone.utc).isoformat())
    log.info("Draft ready: %s -> %s", article["title"], draft["path"])
    return "drafted"


if __name__ == "__main__":
    run()
