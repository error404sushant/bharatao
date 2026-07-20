"""Phase 1 local demo run: A1 Trend Scout -> A2 News Writer -> A9 Publisher (list only).

In production this is 3 separate cron jobs at 05:30 / 06:00 / 08:30 IST
(master plan section 5.1). This script just chains them once so the whole
pipeline can be exercised locally in one shot, per the "run it locally once"
request.
"""

import a1_trend_scout
import a2_news_writer
import a9_publisher
from lib.logger import get_logger

log = get_logger("run_phase1")


def main() -> None:
    log.info("=== Phase 1 demo run starting ===")

    enqueued = a1_trend_scout.run()
    log.info("A1 Trend Scout: %d topic(s) enqueued", enqueued)

    if enqueued == 0:
        log.info("Nothing new to write about (all topics deduped) -- stopping.")
        return

    outcome = a2_news_writer.run()
    log.info("A2 News Writer: %s", outcome)

    log.info("--- A9 Publisher: drafts waiting for your 08:00 human review ---")
    a9_publisher.run_list()

    log.info("=== Phase 1 demo run finished ===")


if __name__ == "__main__":
    main()
