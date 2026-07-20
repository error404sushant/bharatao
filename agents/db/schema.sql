-- Phase 1 SQLite schema (SQLite for Phase 1 -> Postgres in Phase 3, per master plan section 4)

CREATE TABLE IF NOT EXISTS topic_queue (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    topic         TEXT NOT NULL,
    pillar        TEXT NOT NULL,
    score         REAL NOT NULL,
    sources_json  TEXT NOT NULL,   -- JSON array of {title, url, summary}
    status        TEXT NOT NULL DEFAULT 'pending', -- pending | drafted | skipped
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS published_topics (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_key     TEXT NOT NULL UNIQUE, -- normalized topic used for 90-day dedup
    pillar        TEXT NOT NULL,
    published_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    agent         TEXT NOT NULL,      -- e.g. A1, A2, A9
    status        TEXT NOT NULL,      -- success | failed | needs_human
    detail        TEXT,
    started_at    TEXT NOT NULL,
    finished_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
