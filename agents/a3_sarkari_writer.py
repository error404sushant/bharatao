"""A3 Sarkari Writer -- runs 06:30 daily (master plan section 5.1).

Sources from PIB (Press Information Bureau) RSS -- real government press
releases, per master plan section 5.2. PIB's English-language RSS query
params don't reliably return English content (tested: Lang=1/2 both return
Hindi for this feed), so this pulls the Hindi feed and has the writer
translate + explain in English, the same way any newsroom works from a
Hindi wire source. Revisit if PIB's English feed URL is found later.

Sarkari is the highest-stakes pillar (master plan 5.2/7.1) -- the prompt
(sarkari_v1.md) enforces "no fact without a fact_source" harder than any
other writer, and this agent never invents deadlines/amounts/eligibility.
"""

import re

import feedparser
import requests
from datetime import datetime, timezone

from lib import dedup, draft_store, image_maker
from lib.config import PROMPTS_DIR
from lib.llm_client import chat_completion
from lib.logger import get_logger
from lib.validator import validate_article

log = get_logger("A3_sarkari_writer")

SYSTEM_PROMPT = (PROMPTS_DIR / "sarkari_v1.md").read_text()

PIB_RSS = "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3"
MAX_CANDIDATES = 5

# PIB's feed has some XML defect feedparser's strict parser rejects (a
# mismatched-tag error), even though every <item><title>...</title>
# <link>...</link></item> block is individually well-formed. Falling back to
# direct extraction of exactly that shape rather than fighting the parser.
ITEM_RE = re.compile(r"<item>\s*<title>(.*?)</title>\s*<link>(.*?)</link>\s*</item>", re.DOTALL)


def fetch_pib_items() -> list[dict]:
    log.info("Fetching %s", PIB_RSS)
    feed = feedparser.parse(PIB_RSS)
    if not (getattr(feed, "bozo", False) and not feed.entries):
        return [{"title": e.get("title", ""), "link": e.get("link", "")} for e in feed.entries[:MAX_CANDIDATES]]

    log.warning("feedparser rejected PIB feed (%s) -- falling back to regex extraction", getattr(feed, "bozo_exception", "unknown error"))
    try:
        resp = requests.get(PIB_RSS, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        log.warning("PIB RSS raw fetch also failed: %s", exc)
        return []

    # requests mis-guesses the charset for this feed (no charset in its
    # Content-Type header) and mangles the Hindi text -- force real UTF-8.
    text = resp.content.decode("utf-8-sig")
    matches = ITEM_RE.findall(text)
    return [{"title": title.strip(), "link": link.strip()} for title, link in matches[:MAX_CANDIDATES]]


def build_user_prompt(entry) -> str:
    title = entry.get("title", "")
    link = entry.get("link", "")
    return (
        f"SOURCE: a Press Information Bureau (PIB, Government of India) press "
        f"release, originally in Hindi. Title: \"{title}\"\n"
        f"Source URL: {link}\n\n"
        "Translate and explain this announcement for BharatAo readers in "
        "English (Hinglish-friendly). Only state details that are directly "
        "in this title -- if the title doesn't give you a specific date, "
        "amount, or eligibility rule, do not invent one; write "
        "\"abhi confirm nahi hua\" for that detail instead, and note in "
        "fact_sources that readers should check the official PIB link above "
        "for full details.\n"
    )


def run(count: int = 1) -> dict:
    dedup.init_db()
    entries = fetch_pib_items()
    outcome = {"drafted": 0, "needs_human": 0, "duplicate": 0}

    if not entries:
        log.info("No PIB entries available this run.")
        return outcome

    for entry in entries:
        if outcome["drafted"] >= count:
            break
        title = entry.get("title", "").strip()
        if not title or dedup.is_duplicate(title):
            outcome["duplicate"] += 1
            continue

        user_prompt = build_user_prompt(entry)
        errors: list[str] = ["agent API never returned a response"]
        article = None

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
            dedup.log_run("A3", "needs_human", f"title={title!r} errors={errors}", datetime.now(timezone.utc).isoformat())
            log.error("NEEDS_HUMAN: %s -- %s", title, errors)
            outcome["needs_human"] += 1
            continue

        image_maker.make_branded_card(article["title"], "Sarkari", article["slug"])
        draft = draft_store.save_draft(
            title=article["title"],
            html_body=article["html_body"],
            excerpt=article["meta_description"],
            slug=article["slug"],
            tags=article.get("tags", []),
            faq=article.get("faq", []),
            fact_sources=article.get("fact_sources", []),
            category="Sarkari",
        )
        dedup.mark_published(title, "Sarkari")
        dedup.log_run("A3", "success", f"title={title!r} draft={draft}", datetime.now(timezone.utc).isoformat())
        log.info("Draft ready: %s -> %s", article["title"], draft["path"])
        outcome["drafted"] += 1

    log.info("A3 Sarkari Writer done: %s", outcome)
    return outcome


if __name__ == "__main__":
    run()
