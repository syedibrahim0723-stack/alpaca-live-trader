"""The running radar: source tasks, ingest pipeline, classifier queue, topics, push."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid

import httpx
from fastapi import WebSocket

from . import crypto
from .classifier import AIClassifier, keyword_classify
from .db import DB
from .dedupe import Deduper, canon_url, raw_id_for
from .market import Market
from .models import DEFAULT_SETTINGS, RawItem, clean_symbols, extract_tickers
from .sources import REGISTRY, Source, SourceConfig
from .topics import TopicModel, list_topics, rebuild_topics

log = logging.getLogger("news_radar")

AI_BACKFILL_HOURS = 3   # older backfilled stories keep keyword labels to save tokens
BATCH = 10


class Radar:
    def __init__(self, db: DB | None = None):
        self.db = db or DB()
        self._settings = self.db.get_settings(DEFAULT_SETTINGS)
        self.http: httpx.AsyncClient | None = None
        self.deduper = Deduper(self.db, self.settings)
        self.topics = TopicModel()
        self.market = Market()
        self.sources: dict[str, Source] = {}
        self.tasks: dict[str, asyncio.Task] = {}
        self.bg: list[asyncio.Task] = []
        self.clients: set[WebSocket] = set()
        self.classify_q: asyncio.Queue[str] = asyncio.Queue()
        self._clf: tuple[tuple, AIClassifier] | None = None

    # ── settings & source configs ────────────────────────────────────────────
    def settings(self) -> dict:
        return self._settings

    def update_settings(self, values: dict) -> dict:
        allowed = {k: v for k, v in values.items() if k in DEFAULT_SETTINGS}
        if "watchlist" in allowed:
            allowed["watchlist"] = clean_symbols(allowed["watchlist"])
        self.db.put_settings(allowed)
        self._settings = self.db.get_settings(DEFAULT_SETTINGS)
        self.configure_market()
        return self._settings

    def source_config(self, sid: str) -> SourceConfig:
        cls = REGISTRY[sid]
        row = self.db.one("SELECT * FROM sources WHERE id=?", (sid,))
        if not row:
            extra = {f["name"]: f["default"] for f in cls.extra_fields}
            self.db.execute(
                "INSERT INTO sources(id, enabled, plan, poll_seconds, extra) VALUES(?,?,?,?,?)",
                (sid, int(cls.default_enabled), "Free", cls.default_poll, json.dumps(extra)),
            )
            row = self.db.one("SELECT * FROM sources WHERE id=?", (sid,))
        cfg = SourceConfig(
            id=sid, enabled=bool(row["enabled"]), plan=row["plan"] or "Free",
            api_key=crypto.decrypt(row["api_key"]), api_secret=crypto.decrypt(row["api_secret"]),
            poll_seconds=row["poll_seconds"] or cls.default_poll, extra=json.loads(row["extra"] or "{}"),
        )
        # Environment variables fill in keys that were never entered in the UI.
        env = {"alpaca": ("ALPACA_API_KEY", "ALPACA_SECRET_KEY"), "anthropic": ("ANTHROPIC_API_KEY", None)}.get(sid)
        if env:
            cfg.api_key = cfg.api_key or os.getenv(env[0], "")
            if env[1]:
                cfg.api_secret = cfg.api_secret or os.getenv(env[1], "")
        return cfg

    def save_source(self, sid: str, body: dict) -> None:
        cls = REGISTRY[sid]
        self.source_config(sid)  # ensure row
        sets, params = [], []
        if "enabled" in body:
            sets.append("enabled=?"); params.append(int(bool(body["enabled"])))
        if "plan" in body:
            sets.append("plan=?"); params.append(str(body["plan"]))
        if "poll_seconds" in body:
            sets.append("poll_seconds=?"); params.append(max(cls.min_poll, int(body["poll_seconds"])))
        if body.get("api_key"):          # blank = keep the stored key
            sets.append("api_key=?"); params.append(crypto.encrypt(body["api_key"].strip()))
        if body.get("api_secret"):
            sets.append("api_secret=?"); params.append(crypto.encrypt(body["api_secret"].strip()))
        if body.get("clear_key"):
            sets.append("api_key=''"); sets.append("api_secret=''")
        if "extra" in body:
            sets.append("extra=?"); params.append(json.dumps(body["extra"]))
        if sets:
            self.db.execute(f"UPDATE sources SET {', '.join(sets)} WHERE id=?", (*params, sid))

    def source_view(self, sid: str) -> dict:
        cls = REGISTRY[sid]
        cfg = self.source_config(sid)
        src = self.sources.get(sid)
        st = src.status if src else None
        ok, why = (src or cls(cfg, self)).ready()
        return {
            "id": sid, "name": cls.name, "kind": cls.kind, "group": cls.group,
            "needs_key": cls.needs_key, "needs_secret": cls.needs_secret,
            "enabled": cfg.enabled, "plan": cfg.plan, "poll_seconds": cfg.poll_seconds,
            "min_poll": cls.min_poll, "limit_hint": cls.limit_hint, "signup_url": cls.signup_url,
            "key_masked": crypto.mask(cfg.api_key), "secret_masked": crypto.mask(cfg.api_secret),
            "extra": cfg.extra, "extra_fields": cls.extra_fields,
            "state": (st.state if st and cfg.enabled else ("no key" if cfg.enabled and not ok else "off")),
            "detail": st.detail if st and cfg.enabled else why,
            "today": st.today if st else 0, "firsts": st.firsts if st else 0,
            "last_ok": st.last_ok if st else 0,
        }

    # ── lifecycle ────────────────────────────────────────────────────────────
    async def start(self) -> None:
        self.http = httpx.AsyncClient(timeout=20.0, headers={"Accept": "application/json, */*"})
        self.configure_market()
        self.deduper.load_recent()
        for sid in REGISTRY:
            self.restart_source(sid)
        self.bg = [
            asyncio.create_task(self._classifier_worker()),
            asyncio.create_task(self._topic_loop()),
            asyncio.create_task(self._status_loop()),
        ]

    async def stop(self) -> None:
        for t in [*self.tasks.values(), *self.bg]:
            t.cancel()
        if self.http:
            await self.http.aclose()

    def configure_market(self) -> None:
        cfg = self.source_config("alpaca")
        self.market.configure(cfg.api_key, cfg.api_secret, self._settings.get("alpaca_feed", "iex"))

    def restart_source(self, sid: str) -> None:
        old = self.tasks.pop(sid, None)
        if old:
            old.cancel()
        cfg = self.source_config(sid)
        prev = self.sources.get(sid)
        src = REGISTRY[sid](cfg, self)
        if prev:
            src.status.today, src.status.firsts, src.status.day = prev.status.today, prev.status.firsts, prev.status.day
        self.sources[sid] = src
        if sid == "alpaca":
            self.configure_market()
        ok, why = src.ready()
        if not cfg.enabled:
            src.status.state, src.status.detail = "off", ""
            return
        if not ok:
            src.status.state, src.status.detail = "no key", why
            return
        src.status.state, src.status.detail = "starting", ""
        self.tasks[sid] = asyncio.create_task(src.run(), name=f"source:{sid}")

    def classifier(self) -> AIClassifier | None:
        if self._settings.get("classifier") != "ai":
            return None
        cfg = self.source_config("anthropic")
        if not (cfg.enabled and cfg.api_key):
            return None
        sig = (cfg.api_key, self._settings.get("ai_model"))
        if not self._clf or self._clf[0] != sig:
            self._clf = (sig, AIClassifier(*sig))
        return self._clf[1]

    # ── ingest ───────────────────────────────────────────────────────────────
    def is_new(self, row: dict) -> bool:
        window = float(self._settings["new_window_min"]) * 60
        return bool(row["fresh"]) and not row["seen"] and time.time() - row["first_seen"] < window

    def view(self, row: dict) -> dict:
        d = dict(row)
        d["is_new"] = self.is_new(row)
        d.pop("canon_url", None)
        return d

    async def ingest_many(self, src: Source, items: list[RawItem]) -> None:
        new = 0
        for raw in items:
            try:
                if await self.ingest(src, raw):
                    new += 1
            except Exception as e:  # noqa: BLE001 - one bad story must not stop the feed
                log.warning("ingest failed for %s: %s", src.id, e)
        src.status.count(0, firsts=new)

    async def ingest(self, src: Source, raw: RawItem) -> bool:
        """Returns True when the story was new to the radar."""
        headline = (raw.headline or "").strip()
        if not headline:
            return False
        rid = raw_id_for(raw.source, raw.source_id, raw.url, headline)
        if self.deduper.known_raw(rid):
            return False
        src.status.count(1)
        tickers = clean_symbols(list(raw.tickers) + extract_tickers(headline, raw.summary))
        now = time.time()

        dup = self.deduper.match(headline, raw.url, tickers)
        if dup:
            row = self.db.one("SELECT * FROM news WHERE id=?", (dup,))
            if row:
                srcs = row["sources"] + ([raw.source] if raw.source not in row["sources"] else [])
                tk = row["tickers"] + [t for t in tickers if t not in row["tickers"]]
                self.db.execute("UPDATE news SET sources=?, tickers=? WHERE id=?",
                                (json.dumps(srcs), json.dumps(tk), dup))
                self.db.execute("INSERT OR IGNORE INTO raw_ids(raw_id, news_id) VALUES(?,?)", (rid, dup))
                row.update(sources=srcs, tickers=tk)
                await self.broadcast({"type": "update", "item": self.view(row)})
            return False

        published = min(raw.published_at or now, now)
        fresh = int(now - published <= float(self._settings["new_window_min"]) * 60)
        kw = keyword_classify(headline, raw.summary)
        nid = uuid.uuid4().hex[:16]
        row = {
            "id": nid, "headline": headline[:500], "summary": (raw.summary or "")[:2000], "url": raw.url,
            "canon_url": canon_url(raw.url), "published_at": published, "first_seen": now,
            "fresh": fresh, "seen": 0, "source": raw.source, "sources": [raw.source], "tickers": tickers,
            "category": kw["category"], "sentiment": raw.provider_sentiment or kw["sentiment"],
            "impact": kw["impact"], "ai_summary": "", "classified_by": "keywords",
            "topic_id": self.topics.assign(f"{headline}. {raw.summary[:300]}"),
            "publisher": raw.publisher,
        }
        self.db.execute(
            "INSERT INTO news(id, headline, summary, url, canon_url, published_at, first_seen, fresh, seen,"
            " source, sources, tickers, category, sentiment, impact, ai_summary, classified_by, topic_id)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (nid, row["headline"], row["summary"], row["url"], row["canon_url"], published, now, fresh, 0,
             raw.source, json.dumps([raw.source]), json.dumps(tickers), row["category"], row["sentiment"],
             row["impact"], "", "keywords", row["topic_id"]),
        )
        self.db.execute("INSERT OR IGNORE INTO raw_ids(raw_id, news_id) VALUES(?,?)", (rid, nid))
        self.deduper.remember(nid, headline, tickers, now)
        if now - published <= AI_BACKFILL_HOURS * 3600:
            self.classify_q.put_nowait(nid)
        row.pop("publisher")
        await self.broadcast({"type": "news", "item": self.view(row)})
        return True

    # ── background loops ─────────────────────────────────────────────────────
    async def _classifier_worker(self) -> None:
        while True:
            first = await self.classify_q.get()
            ids = [first]
            deadline = time.monotonic() + 1.5
            while len(ids) < BATCH and time.monotonic() < deadline:
                try:
                    ids.append(await asyncio.wait_for(self.classify_q.get(), deadline - time.monotonic()))
                except asyncio.TimeoutError:
                    break
            clf = self.classifier()
            if not clf:
                continue
            rows = self.db.query(f"SELECT * FROM news WHERE id IN ({','.join('?' * len(ids))})", ids)
            try:
                results = await clf.classify(rows)
                if "anthropic" in self.sources:
                    self.sources["anthropic"].status.state = "ok"
                    self.sources["anthropic"].status.detail = f"last batch {time.strftime('%H:%M:%S')}"
                    self.sources["anthropic"].status.count(len(results))
            except Exception as e:  # noqa: BLE001
                log.warning("AI classification failed: %s", e)
                if "anthropic" in self.sources:
                    self.sources["anthropic"].status.state = "error"
                    self.sources["anthropic"].status.detail = str(e)[:160]
                continue
            for row in rows:
                r = results.get(row["id"])
                if not r:
                    continue
                tickers = r["tickers"] or row["tickers"]
                self.db.execute(
                    "UPDATE news SET category=?, sentiment=?, impact=?, tickers=?, ai_summary=?, classified_by='ai'"
                    " WHERE id=?",
                    (r["category"], r["sentiment"], r["impact"], json.dumps(tickers), r["summary"], row["id"]),
                )
                row.update(category=r["category"], sentiment=r["sentiment"], impact=r["impact"],
                           tickers=tickers, ai_summary=r["summary"], classified_by="ai")
                await self.broadcast({"type": "update", "item": self.view(row)})

    async def refresh_topics(self) -> list[dict]:
        topics = await rebuild_topics(self.db, self.topics, self.classifier())
        await self.broadcast({"type": "topics", "topics": topics})
        return topics

    async def _topic_loop(self) -> None:
        await asyncio.sleep(20)
        while True:
            try:
                await self.refresh_topics()
            except Exception as e:  # noqa: BLE001
                log.warning("topic rebuild failed: %s", e)
            await asyncio.sleep(max(2, float(self._settings["topic_refresh_min"])) * 60)

    async def _status_loop(self) -> None:
        while True:
            await asyncio.sleep(5)
            if self.clients:
                await self.broadcast({"type": "status", "sources": self.status_list()})

    def status_list(self) -> list[dict]:
        out = []
        for sid in REGISTRY:
            v = self.source_view(sid)
            out.append({k: v[k] for k in ("id", "name", "group", "enabled", "state", "detail", "today", "firsts")})
        return out

    # ── push ─────────────────────────────────────────────────────────────────
    async def broadcast(self, msg: dict) -> None:
        if not self.clients:
            return
        text = json.dumps(msg)
        dead = []
        for ws in list(self.clients):
            try:
                await ws.send_text(text)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)

    def recent(self, limit=300, category=None, ticker=None, topic=None, new_only=False) -> list[dict]:
        sql, params = "SELECT * FROM news WHERE 1=1", []
        if category:
            sql += " AND category=?"; params.append(category)
        if topic is not None:
            sql += " AND topic_id=?"; params.append(int(topic))
        if ticker:
            sql += " AND tickers LIKE ?"; params.append(f'%"{ticker.upper()}"%')
        sql += " ORDER BY published_at DESC LIMIT ?"
        params.append(int(limit) * (3 if new_only else 1))
        rows = [self.view(r) for r in self.db.query(sql, params)]
        if new_only:
            rows = [r for r in rows if r["is_new"]]
        return rows[:limit]

    def topic_list(self) -> list[dict]:
        return list_topics(self.db)
