"""A2 News Writer -- runs 06:00 daily (master plan section 5.1 / 5.4).

For each top pending topic in topic_queue:
  1. build source snippets from the RSS entry A1 already collected
  2. call the AGENT API with the writer prompt contract (prompts/news_v1.md)
  3. validate the strict-JSON response (code validator, not the model)
  4. on pass: A8 Image Maker -> save draft to data/drafts/ for human review
  5. on fail (after one retry): mark NEEDS_HUMAN, do not publish anything
"""

import json
from datetime import datetime, timezone

import requests

from lib import dedup, draft_store, image_maker
from lib.config import NEWS_WRITER_COUNT, PROMPTS_DIR
from lib.llm_client import chat_completion
from lib.logger import get_logger
from lib.validator import validate_article

log = get_logger("A2_news_writer")

SYSTEM_PROMPT = (PROMPTS_DIR / "news_v1.md").read_text()


def build_user_prompt(topic_row) -> str:
    sources = json.loads(topic_row["sources_json"])
    sources_block = "\n".join(f"- {s['title']}: {s['summary']} ({s['url']})" for s in sources)
    return (
        f"TOPIC: {topic_row['topic']}\n"
        f"PILLAR: {topic_row['pillar']}\n"
        f"TARGET KEYWORD: {topic_row['topic']}\n\n"
        f"SOURCE SNIPPETS:\n{sources_block}\n\n"
        "EXISTING BHARATAO URLS FOR INTERNAL LINKS: (none yet -- site is new, omit internal links)\n"
    )


def write_one(topic_row) -> str:
    """Returns status: 'drafted' | 'needs_human' | 'duplicate'."""
    if dedup.is_duplicate(topic_row["topic"]):
        # This pending row was queued before an earlier run published the same
        # (or a near-identically worded) story. A1 only blocks *new* enqueues
        # against published_topics -- older sibling rows already sitting in
        # the backlog need this same check here, or they'd get redrafted.
        dedup.mark_topic(topic_row["id"], "skipped")
        log.info("Skip (already published, stale queue row): %s", topic_row["topic"])
        return "duplicate"

    user_prompt = build_user_prompt(topic_row)
    errors: list[str] = ["agent API never returned a response"]

    for attempt in (1, 2, 3):
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
        dedup.mark_topic(topic_row["id"], "skipped")
        dedup.log_run("A2", "needs_human", f"topic={topic_row['topic']!r} errors={errors}", datetime.now(timezone.utc).isoformat())
        log.error("NEEDS_HUMAN: %s -- %s", topic_row["topic"], errors)
        return "needs_human"

    image_maker.make_branded_card(article["title"], topic_row["pillar"], article["slug"])
    draft = draft_store.save_draft(
        title=article["title"],
        html_body=article["html_body"],
        excerpt=article["meta_description"],
        slug=article["slug"],
        tags=article.get("tags", []),
        faq=article.get("faq", []),
        fact_sources=article.get("fact_sources", []),
        category=article.get("category", topic_row["pillar"]),
    )

    dedup.mark_topic(topic_row["id"], "drafted")
    dedup.mark_published(topic_row["topic"], topic_row["pillar"])
    dedup.log_run("A2", "success", f"topic={topic_row['topic']!r} draft={draft}", datetime.now(timezone.utc).isoformat())
    log.info("Draft ready: %s -> %s", article["title"], draft["path"])
    return "drafted"


def run(count: int = NEWS_WRITER_COUNT) -> dict:
    dedup.init_db()
    outcome = {"drafted": 0, "needs_human": 0, "duplicate": 0}
    seen_ids: set[int] = set()

    # Pull extra rounds so stale duplicate rows don't silently reduce the
    # day's output below `count` -- capped so a fully-duplicate backlog can't
    # spin forever.
    for _ in range(count * 3 + 10):
        if outcome["drafted"] >= count:
            break
        batch = [t for t in dedup.next_pending_topics(count) if t["id"] not in seen_ids]
        if not batch:
            break
        topic_row = batch[0]
        seen_ids.add(topic_row["id"])
        status = write_one(topic_row)
        outcome[status] += 1

    if outcome == {"drafted": 0, "needs_human": 0, "duplicate": 0}:
        log.info("No pending topics in topic_queue -- run A1 Trend Scout first.")

    log.info("A2 News Writer done: %s", outcome)
    return outcome


if __name__ == "__main__":
    run()
