"""Price data from Alpaca: snapshot, intraday bars and daily bars."""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone

from alpaca.data.enums import DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockSnapshotRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from .technicals import build_report

TIMEFRAMES = {
    "1m": (TimeFrame(1, TimeFrameUnit.Minute), 2),
    "5m": (TimeFrame(5, TimeFrameUnit.Minute), 5),
    "15m": (TimeFrame(15, TimeFrameUnit.Minute), 10),
    "1H": (TimeFrame(1, TimeFrameUnit.Hour), 30),
    "1D": (TimeFrame(1, TimeFrameUnit.Day), 400),
}


def _bars(resp, sym: str) -> list[dict]:
    data = getattr(resp, "data", {}) or {}
    return [
        {"t": b.timestamp.timestamp(), "o": float(b.open), "h": float(b.high),
         "l": float(b.low), "c": float(b.close), "v": float(b.volume)}
        for b in data.get(sym, [])
    ]


class Market:
    def __init__(self):
        self.client: StockHistoricalDataClient | None = None
        self._creds: tuple[str, str] | None = None
        self.feed = DataFeed.IEX
        self._cache: dict[tuple, tuple[float, dict]] = {}

    def configure(self, key: str, secret: str, feed: str) -> None:
        self.feed = DataFeed.SIP if feed == "sip" else DataFeed.IEX
        if key and secret and (key, secret) != self._creds:
            self.client = StockHistoricalDataClient(key, secret)
            self._creds = (key, secret)
            self._cache.clear()

    @property
    def ready(self) -> bool:
        return self.client is not None

    def _fetch_bars(self, sym: str, tf: str) -> list[dict]:
        timeframe, days = TIMEFRAMES[tf]
        req = StockBarsRequest(
            symbol_or_symbols=sym, timeframe=timeframe, feed=self.feed,
            start=datetime.now(timezone.utc) - timedelta(days=days),
        )
        return _bars(self.client.get_stock_bars(req), sym)

    def _fetch_snapshot(self, sym: str) -> dict:
        snap = self.client.get_stock_snapshot(StockSnapshotRequest(symbol_or_symbols=sym, feed=self.feed))[sym]
        lt, lq, db, pb = snap.latest_trade, snap.latest_quote, snap.daily_bar, snap.previous_daily_bar
        return {
            "price": float(lt.price) if lt else None,
            "bid": float(lq.bid_price) if lq else None,
            "ask": float(lq.ask_price) if lq else None,
            "open": float(db.open) if db else None,
            "high": float(db.high) if db else None,
            "low": float(db.low) if db else None,
            "volume": float(db.volume) if db else None,
            "prev_close": float(pb.close) if pb else None,
        }

    def _report(self, sym: str, tf: str, news_ts: float | None) -> dict:
        snap = self._fetch_snapshot(sym)
        intraday = self._fetch_bars(sym, "5m")
        daily = self._fetch_bars(sym, "1D")
        chart = intraday if tf == "5m" else daily if tf == "1D" else self._fetch_bars(sym, tf)
        rep = build_report(intraday, daily, snap, news_ts)
        rep["symbol"] = sym
        rep["timeframe"] = tf
        rep["bars"] = chart[-600:]
        rep["feed"] = self.feed.value
        return rep

    async def report(self, sym: str, tf: str = "5m", news_ts: float | None = None) -> dict:
        if not self.ready:
            raise RuntimeError("Add your Alpaca key and secret on the Sources page to load prices.")
        if tf not in TIMEFRAMES:
            tf = "5m"
        key = (sym, tf, int(news_ts or 0))
        hit = self._cache.get(key)
        if hit and time.time() - hit[0] < 10:
            return hit[1]
        rep = await asyncio.to_thread(self._report, sym, tf, news_ts)
        self._cache[key] = (time.time(), rep)
        if len(self._cache) > 200:
            self._cache.clear()
        return rep
