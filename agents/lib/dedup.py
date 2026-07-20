import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

from lib.config import DB_PATH, SCHEMA_PATH

DEDUP_WINDOW_DAYS = 90


def normalize_topic(topic: str) -> str:
    key = topic.lower().strip()
    key = re.sub(r"[^a-z0-9\s]", "", key)
    key = re.sub(r"\s+", " ", key)
    return key


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA_PATH.read_text())


def is_duplicate(topic: str) -> bool:
    key = normalize_topic(topic)
    cutoff = (datetime.utcnow() - timedelta(days=DEDUP_WINDOW_DAYS)).isoformat()
    with connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM published_topics WHERE topic_key = ? AND published_at >= ?",
            (key, cutoff),
        ).fetchone()
    return row is not None


def enqueue_topic(topic: str, pillar: str, score: float, sources: list[dict]) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO topic_queue (topic, pillar, score, sources_json) VALUES (?, ?, ?, ?)",
            (topic, pillar, score, json.dumps(sources)),
        )
        return cur.lastrowid


def next_pending_topics(limit: int) -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM topic_queue WHERE status = 'pending' ORDER BY score DESC, id ASC LIMIT ?",
            (limit,),
        ).fetchall()


def mark_topic(topic_id: int, status: str) -> None:
    with connect() as conn:
        conn.execute("UPDATE topic_queue SET status = ? WHERE id = ?", (status, topic_id))


def mark_published(topic: str, pillar: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO published_topics (topic_key, pillar) VALUES (?, ?)",
            (normalize_topic(topic), pillar),
        )


def log_run(agent: str, status: str, detail: str, started_at: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO agent_runs (agent, status, detail, started_at) VALUES (?, ?, ?, ?)",
            (agent, status, detail, started_at),
        )
