"""A1 Trend Scout -- runs 05:30 daily (master plan section 5.1).

Collects trending topics + raw data. Writes NOTHING (no articles). Fills the
topic_queue, deduped against published_topics (last 90 days).

Phase 1 data source: Google News India RSS (free, reliable, legal -- section
5.2). Google Trends / PIB / job portals plug in the same way in Phase 2.
"""

from datetime import datetime, timezone

import feedparser

from lib import dedup
from lib.logger import get_logger

log = get_logger("A1_trend_scout")

GOOGLE_NEWS_INDIA_RSS = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
MAX_TOPICS = 8

# Used only if the network/RSS fetch fails, so the pipeline can still be
# exercised locally without connectivity.
OFFLINE_FALLBACK_TOPICS = [
    {
        "topic": "PM Kisan 19th installment release date",
        "pillar": "Sarkari",
        "sources": [{"title": "PM Kisan scheme update", "url": "https://pmkisan.gov.in", "summary": "Installment release schedule for eligible farmers."}],
    },
]


def fetch_entries() -> list[dict]:
    log.info("Fetching %s", GOOGLE_NEWS_INDIA_RSS)
    feed = feedparser.parse(GOOGLE_NEWS_INDIA_RSS)
    if getattr(feed, "bozo", False) and not feed.entries:
        log.warning("RSS fetch failed (%s) -- using offline fallback topics", getattr(feed, "bozo_exception", "unknown error"))
        return []
    return feed.entries[:MAX_TOPICS]


def score_entry(entry: dict, index: int) -> float:
    # freshness: earlier in the feed = higher score. No search-volume signal
    # available yet in Phase 1, so position acts as the proxy.
    return round(1.0 - (index * 0.05), 3)


def run() -> int:
    started_at = datetime.now(timezone.utc).isoformat()
    dedup.init_db()

    entries = fetch_entries()
    enqueued = 0

    if entries:
        for i, entry in enumerate(entries):
            title = entry.get("title", "").strip()
            if not title:
                continue
            if dedup.is_duplicate(title):
                log.info("Skip (published within 90 days): %s", title)
                continue
            source = {
                "title": title,
                "url": entry.get("link", ""),
                "summary": entry.get("summary", ""),
            }
            dedup.enqueue_topic(title, pillar="News", score=score_entry(entry, i), sources=[source])
            enqueued += 1
            log.info("Enqueued: %s", title)
    else:
        for item in OFFLINE_FALLBACK_TOPICS:
            if dedup.is_duplicate(item["topic"]):
                continue
            dedup.enqueue_topic(item["topic"], pillar=item["pillar"], score=0.5, sources=item["sources"])
            enqueued += 1
            log.info("Enqueued (offline fallback): %s", item["topic"])

    dedup.log_run("A1", "success", f"enqueued={enqueued}", started_at)
    log.info("A1 Trend Scout done. %d topics enqueued.", enqueued)
    return enqueued


if __name__ == "__main__":
    run()
