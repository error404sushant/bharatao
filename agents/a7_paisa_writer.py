"""A7 Paisa Writer -- runs Tue & Fri 08:00 (master plan section 5.1).

Evergreen personal-finance explainer, same shape as A6 Gyaan: not sourced
from A1's RSS topic_queue, generates one topic per run, always saves as a
draft for human review (master plan 5.4) regardless of pillar risk level.
"""

import requests
from datetime import datetime, timezone

from lib import dedup, draft_store, image_maker
from lib.config import PROMPTS_DIR
from lib.llm_client import chat_completion
from lib.logger import get_logger
from lib.validator import validate_article

log = get_logger("A7_paisa_writer")

SYSTEM_PROMPT = (PROMPTS_DIR / "paisa_v1.md").read_text()

# Rotated so repeated runs don't converge on the same "SIP" explainer every time.
TOPIC_POOL = [
    "how SIPs (Systematic Investment Plans) work",
    "what a credit score is and why it matters",
    "old tax regime vs new tax regime -- how to choose",
    "what an emergency fund is and how big it should be",
    "how PPF (Public Provident Fund) works",
    "term insurance basics -- what it covers and why it's cheap",
    "how compound interest actually works with a simple example",
    "what a mutual fund expense ratio means",
]


def pick_topic() -> str:
    for topic in TOPIC_POOL:
        if not dedup.is_duplicate(topic):
            return topic
    return TOPIC_POOL[0]  # all covered recently -- refresh the oldest one


def build_user_prompt(topic: str) -> str:
    return f"Today's explainer topic: {topic}\n"


def run() -> str:
    """Returns status: 'drafted' | 'needs_human'."""
    dedup.init_db()
    topic = pick_topic()
    user_prompt = build_user_prompt(topic)
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
        dedup.log_run("A7", "needs_human", f"topic={topic!r} errors={errors}", datetime.now(timezone.utc).isoformat())
        log.error("NEEDS_HUMAN: %s -- %s", topic, errors)
        return "needs_human"

    image_maker.make_branded_card(article["title"], "Paisa", article["slug"])
    draft = draft_store.save_draft(
        title=article["title"],
        html_body=article["html_body"],
        excerpt=article["meta_description"],
        slug=article["slug"],
        tags=article.get("tags", []),
        faq=article.get("faq", []),
        fact_sources=article.get("fact_sources", []),
        category="Paisa",
    )

    dedup.mark_published(topic, "Paisa")
    dedup.log_run("A7", "success", f"topic={topic!r} draft={draft}", datetime.now(timezone.utc).isoformat())
    log.info("Draft ready: %s -> %s", article["title"], draft["path"])
    return "drafted"


if __name__ == "__main__":
    run()
