"""Benzinga news through Alpaca: WebSocket stream plus a REST backfill."""
from __future__ import annotations

import asyncio
import threading
import time
from datetime import datetime, timedelta, timezone

from alpaca.data.historical import NewsClient
from alpaca.data.live.news import NewsDataStream
from alpaca.data.requests import NewsRequest

from ..models import RawItem, clean_symbols
from .base import Source, log


def _to_raw(a) -> RawItem:
    get = (lambda k: a.get(k)) if isinstance(a, dict) else (lambda k: getattr(a, k, None))
    created = get("created_at")
    if isinstance(created, str):
        created = datetime.fromisoformat(created.replace("Z", "+00:00"))
    return RawItem(
        source="alpaca",
        source_id=str(get("id") or ""),
        headline=get("headline") or "",
        summary=get("summary") or "",
        url=get("url") or "",
        published_at=created.timestamp() if created else time.time(),
        tickers=clean_symbols(get("symbols")),
        publisher=get("source") or "benzinga",
    )


class AlpacaNews(Source):
    id = "alpaca"
    name = "Alpaca (Benzinga news + market data)"
    kind = "News WebSocket stream · also supplies prices and bars for the technicals panel"
    group = "platform"
    needs_secret = True
    default_poll = 30
    default_enabled = True
    limit_hint = "News included with any Alpaca account · free data plan uses the IEX feed"
    signup_url = "https://app.alpaca.markets/signup"

    def _backfill(self) -> list[RawItem]:
        client = NewsClient(self.cfg.api_key, self.cfg.api_secret)
        req = NewsRequest(start=datetime.now(timezone.utc) - timedelta(hours=6), limit=50)
        resp = client.get_news(req)
        arts = resp.data.get("news", []) if hasattr(resp, "data") else []
        return [_to_raw(a) for a in arts]

    async def fetch(self, http) -> list[RawItem]:
        return await asyncio.to_thread(self._backfill)

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        try:
            await self.ctx.ingest_many(self, await self.fetch(None))
        except Exception as e:  # noqa: BLE001
            log.warning("alpaca backfill failed: %s", e)

        stream = NewsDataStream(self.cfg.api_key, self.cfg.api_secret)

        async def on_news(data):
            loop.call_soon_threadsafe(queue.put_nowait, _to_raw(data))

        stream.subscribe_news(on_news, "*")
        failed = threading.Event()

        def runner():
            try:
                stream.run()
            except Exception as e:  # noqa: BLE001
                log.warning("alpaca news stream stopped: %s", e)
            failed.set()

        threading.Thread(target=runner, daemon=True, name="alpaca-news").start()
        self.status.state, self.status.detail = "live", "streaming"
        try:
            while True:
                try:
                    raw = await asyncio.wait_for(queue.get(), timeout=30)
                    await self.ctx.ingest_many(self, [raw])
                    self.status.last_ok = time.time()
                except asyncio.TimeoutError:
                    pass
                if failed.is_set():
                    # Stream died (bad keys, connection limit): fall back to REST polling.
                    self.status.state, self.status.detail = "ok", "stream down · polling REST"
                    await super().run()
                    return
        finally:
            try:
                stream.stop()
            except Exception:  # noqa: BLE001
                pass
