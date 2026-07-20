"""Local dev scheduler mirroring deploy/crontab.txt (master plan section 5.1,
Asia/Kolkata). Runs continuously and fires each agent at its IST time slot.

This is a Phase-1 stand-in for real cron on the VPS -- useful for running the
whole thing on a laptop, or for local testing before deploying crontab.txt.

Usage:
    python scheduler.py            # runs forever, fires at 05:30/06:00/08:30 IST
    python scheduler.py --fire-now # fires all three once immediately, then exits
"""

import subprocess
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from lib.logger import get_logger

log = get_logger("scheduler")

IST = ZoneInfo("Asia/Kolkata")

SCHEDULE = [
    ("05:30", "a1_trend_scout.py", []),
    ("06:00", "a2_news_writer.py", []),
    ("08:30", "a9_publisher.py", ["--list"]),
]


def run_agent(script: str, args: list[str]) -> None:
    log.info("Firing %s %s", script, " ".join(args))
    result = subprocess.run([sys.executable, script, *args], capture_output=False)
    if result.returncode != 0:
        log.error("%s exited with code %d", script, result.returncode)
    else:
        log.info("%s finished OK", script)


def fire_now() -> None:
    for _, script, args in SCHEDULE:
        run_agent(script, args)


def run_forever() -> None:
    log.info("Scheduler started. Watching for: %s", [(t, s) for t, s, _ in SCHEDULE])
    fired_today: set[str] = set()
    last_date = None

    while True:
        now = datetime.now(IST)
        today = now.date().isoformat()
        if today != last_date:
            fired_today.clear()
            last_date = today

        hhmm = now.strftime("%H:%M")
        for slot_time, script, args in SCHEDULE:
            key = f"{today}:{slot_time}:{script}"
            if hhmm == slot_time and key not in fired_today:
                fired_today.add(key)
                run_agent(script, args)

        time.sleep(20)


if __name__ == "__main__":
    if "--fire-now" in sys.argv:
        fire_now()
    else:
        run_forever()
