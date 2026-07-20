"""A6 Gyaan Writer -- runs 07:30 daily (master plan section 5.1).

Unlike A2 (which drafts from A1's RSS topic_queue), Gyaan content is evergreen
general knowledge, not breaking news -- so this agent doesn't depend on A1.
It generates one "Daily GK Quiz" article per run and always saves it as a
draft for human review, same as every other writer (master plan 5.4) --
low-risk pillar or not, nothing auto-publishes in Phase 1/2.
"""

import requests
from datetime import datetime, timezone

from lib import dedup, draft_store, image_maker
from lib.config import PROMPTS_DIR
from lib.llm_client import chat_completion
from lib.logger import get_logger
from lib.validator import validate_article

log = get_logger("A6_gyaan_writer")

SYSTEM_PROMPT = (PROMPTS_DIR / "gyaan_v1.md").read_text()


def build_user_prompt() -> str:
    today = datetime.now(timezone.utc).strftime("%A, %d %B %Y")
    return (
        f"Today's date: {today}\n"
        "Write today's Daily GK Quiz: 10 questions mixing History, Geography, "
        "Polity, Science, Sports, and one India current-affairs-flavored "
        "question (general/evergreen, not tied to a specific breaking story).\n"
    )


def run() -> str:
    """Returns status: 'drafted' | 'needs_human' | 'duplicate'."""
    dedup.init_db()
    today_key = f"Daily GK Quiz {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"

    if dedup.is_duplicate(today_key):
        log.info("Skip: already published a Gyaan quiz today")
        dedup.log_run("A6", "success", "already published today", datetime.now(timezone.utc).isoformat())
        return "duplicate"

    user_prompt = build_user_prompt()
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
        dedup.log_run("A6", "needs_human", f"errors={errors}", datetime.now(timezone.utc).isoformat())
        log.error("NEEDS_HUMAN: %s", errors)
        return "needs_human"

    image_maker.make_branded_card(article["title"], "Gyaan", article["slug"])
    draft = draft_store.save_draft(
        title=article["title"],
        html_body=article["html_body"],
        excerpt=article["meta_description"],
        slug=article["slug"],
        tags=article.get("tags", []),
        faq=article.get("faq", []),
        fact_sources=article.get("fact_sources", []),
        category="Gyaan",
    )

    dedup.mark_published(today_key, "Gyaan")
    dedup.log_run("A6", "success", f"draft={draft}", datetime.now(timezone.utc).isoformat())
    log.info("Draft ready: %s -> %s", article["title"], draft["path"])
    return "drafted"


if __name__ == "__main__":
    run()
