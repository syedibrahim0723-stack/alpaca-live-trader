"""SQLite storage: news items, source configs (keys encrypted), settings, topics."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("NEWS_RADAR_DATA", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "news_radar.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS news(
    id TEXT PRIMARY KEY,
    headline TEXT NOT NULL,
    summary TEXT DEFAULT '',
    url TEXT DEFAULT '',
    canon_url TEXT DEFAULT '',
    published_at REAL,
    first_seen REAL,
    fresh INTEGER DEFAULT 0,          -- 1 = first seen while still recent ("NEW")
    seen INTEGER DEFAULT 0,           -- user acknowledged
    source TEXT,                      -- first source that delivered it
    sources TEXT DEFAULT '[]',        -- every source that delivered it (JSON)
    tickers TEXT DEFAULT '[]',
    category TEXT DEFAULT 'Other',
    sentiment TEXT DEFAULT 'neutral',
    impact INTEGER DEFAULT 1,
    ai_summary TEXT DEFAULT '',
    classified_by TEXT DEFAULT '',
    topic_id INTEGER
);
CREATE INDEX IF NOT EXISTS ix_news_first_seen ON news(first_seen);
CREATE INDEX IF NOT EXISTS ix_news_canon ON news(canon_url);
CREATE TABLE IF NOT EXISTS raw_ids(raw_id TEXT PRIMARY KEY, news_id TEXT);
CREATE TABLE IF NOT EXISTS sources(
    id TEXT PRIMARY KEY,
    enabled INTEGER DEFAULT 0,
    plan TEXT DEFAULT 'Free',
    api_key TEXT DEFAULT '',
    api_secret TEXT DEFAULT '',
    poll_seconds INTEGER,
    extra TEXT DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS topics(
    id INTEGER PRIMARY KEY,
    label TEXT,
    terms TEXT,
    size INTEGER,
    updated REAL
);
"""

JSON_COLS = ("sources", "tickers")


class DB:
    def __init__(self, path: Path | str = DB_PATH):
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock:
            self.conn.executescript(SCHEMA)
            self.conn.commit()

    def execute(self, sql: str, params: tuple | list = ()) -> None:
        with self.lock:
            self.conn.execute(sql, params)
            self.conn.commit()

    def executemany(self, sql: str, rows: list) -> None:
        with self.lock:
            self.conn.executemany(sql, rows)
            self.conn.commit()

    def query(self, sql: str, params: tuple | list = ()) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.conn.execute(sql, params).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            for c in JSON_COLS:
                if c in d and isinstance(d[c], str):
                    try:
                        d[c] = json.loads(d[c])
                    except ValueError:
                        d[c] = []
            out.append(d)
        return out

    def one(self, sql: str, params: tuple | list = ()) -> dict[str, Any] | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    # ── settings ──────────────────────────────────────────────────────────────
    def get_settings(self, defaults: dict) -> dict:
        s = dict(defaults)
        for r in self.query("SELECT k, v FROM settings"):
            try:
                s[r["k"]] = json.loads(r["v"])
            except ValueError:
                pass
        return s

    def put_settings(self, values: dict) -> None:
        self.executemany(
            "INSERT INTO settings(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
            [(k, json.dumps(v)) for k, v in values.items()],
        )
