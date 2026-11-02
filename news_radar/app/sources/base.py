"""Source plumbing: each provider is a Source subclass that yields RawItems."""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

from ..models import RawItem

log = logging.getLogger("news_radar.sources")


@dataclass
class SourceConfig:
    id: str
    enabled: bool = False
    plan: str = "Free"
    api_key: str = ""
    api_secret: str = ""
    poll_seconds: int = 60
    extra: dict = field(default_factory=dict)


@dataclass
class SourceStatus:
    state: str = "off"              # off | starting | live | ok | error | no key
    detail: str = ""
    last_ok: float = 0.0
    today: int = 0                  # stories delivered today
    firsts: int = 0                 # stories this source delivered before anyone else
    day: str = ""

    def count(self, n: int, firsts: int = 0) -> None:
        d = time.strftime("%Y-%m-%d")
        if d != self.day:
            self.day, self.today, self.firsts = d, 0, 0
        self.today += n
        self.firsts += firsts


class Source:
    id = ""
    name = ""
    kind = ""                       # shown under the name on the Sources page
    group = "news"                  # "news" or "platform" (Alpaca, Anthropic)
    needs_key = True
    needs_secret = False
    default_poll = 60
    min_poll = 5
    default_enabled = False
    limit_hint = ""
    signup_url = ""
    extra_fields: list[dict] = []   # [{"name", "label", "type": "text|lines", "default"}]

    def __init__(self, cfg: SourceConfig, ctx):
        self.cfg = cfg
        self.ctx = ctx              # App context: settings, ingest, http client, etc.
        self.status = SourceStatus()

    # Subclasses implement fetch(); streaming sources override run().
    async def fetch(self, http: httpx.AsyncClient) -> list[RawItem]:
        raise NotImplementedError

    async def run(self) -> None:
        while True:
            try:
                items = await self.fetch(self.ctx.http)
                await self.ctx.ingest_many(self, items)
                self.status.state, self.status.detail = "ok", f"last pull {time.strftime('%H:%M:%S')}"
                self.status.last_ok = time.time()
            except asyncio.CancelledError:
                raise
            except httpx.HTTPStatusError as e:
                self.status.state = "error"
                self.status.detail = f"HTTP {e.response.status_code}"
                log.warning("%s: %s", self.id, e)
            except Exception as e:  # noqa: BLE001
                self.status.state, self.status.detail = "error", str(e)[:160]
                log.warning("%s: %s", self.id, e)
            await asyncio.sleep(max(self.min_poll, int(self.cfg.poll_seconds or self.default_poll)))

    async def test(self) -> str:
        items = await self.fetch(self.ctx.http)
        return f"OK · {len(items)} stories returned"

    def ready(self) -> tuple[bool, str]:
        if self.needs_key and not self.cfg.api_key:
            return False, "add a key to enable"
        if self.needs_secret and not self.cfg.api_secret:
            return False, "add the secret to enable"
        return True, ""

    def watchlist(self) -> list[str]:
        return list(self.ctx.settings().get("watchlist") or [])


# ── parsing helpers ──────────────────────────────────────────────────────────
def ts_from_iso(s: str | None) -> float:
    if not s:
        return time.time()
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(s).timestamp()
    except (TypeError, ValueError):
        return time.time()


def ts_from_struct(st) -> float:
    if not st:
        return time.time()
    return datetime(*st[:6], tzinfo=timezone.utc).timestamp()
