"""Indicator math (pure numpy) and the price-action report for one ticker."""
from __future__ import annotations

from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

import numpy as np

ET = ZoneInfo("America/New_York")


def ema(x: np.ndarray, n: int) -> np.ndarray:
    out = np.empty_like(x, dtype=float)
    if len(x) == 0:
        return out
    a = 2.0 / (n + 1)
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def rsi(close: np.ndarray, n: int = 14) -> float | None:
    if len(close) <= n:
        return None
    d = np.diff(close)
    gain, loss = np.clip(d, 0, None), np.clip(-d, 0, None)
    ag, al = gain[:n].mean(), loss[:n].mean()
    for g, l in zip(gain[n:], loss[n:]):  # Wilder smoothing
        ag = (ag * (n - 1) + g) / n
        al = (al * (n - 1) + l) / n
    if al == 0:
        return 100.0
    return float(100 - 100 / (1 + ag / al))


def macd(close: np.ndarray) -> tuple[float, float, float] | None:
    if len(close) < 35:
        return None
    line = ema(close, 12) - ema(close, 26)
    sig = ema(line, 9)
    return float(line[-1]), float(sig[-1]), float(line[-1] - sig[-1])


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int = 14) -> float | None:
    if len(close) <= n:
        return None
    prev = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum(high - low, np.maximum(abs(high - prev), abs(low - prev)))
    return float(ema(tr, n)[-1])


def _arr(bars: list[dict], k: str) -> np.ndarray:
    return np.array([b[k] for b in bars], dtype=float)


def _et(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, ET)


def _pct(a: float | None, b: float | None) -> float | None:
    if a is None or not b:
        return None
    return round((a - b) / b * 100, 2)


def _r(x, nd=2):
    return None if x is None else round(float(x), nd)


def build_report(intraday: list[dict], daily: list[dict], snap: dict, news_ts: float | None = None) -> dict:
    """intraday: 1-min or 5-min bars (incl. extended hours) for recent days.
    daily: ~300 daily bars. Bars are dicts with t (epoch s), o, h, l, c, v."""
    last = snap.get("price") or (intraday[-1]["c"] if intraday else None)
    prev_close = snap.get("prev_close") or (daily[-2]["c"] if len(daily) >= 2 else None)

    # Split today's session from earlier bars.
    today = _et(intraday[-1]["t"]).date() if intraday else None
    today_bars = [b for b in intraday if _et(b["t"]).date() == today]
    pre = [b for b in today_bars if _et(b["t"]).time() < dtime(9, 30)]
    reg = [b for b in today_bars if dtime(9, 30) <= _et(b["t"]).time() < dtime(16, 0)]
    first30 = [b for b in reg if _et(b["t"]).time() < dtime(10, 0)]

    # VWAP over the regular session (or premarket if the session hasn't opened).
    vw_src = reg or pre
    vwap = None
    if vw_src:
        tp = (_arr(vw_src, "h") + _arr(vw_src, "l") + _arr(vw_src, "c")) / 3
        v = _arr(vw_src, "v")
        vwap = float((tp * v).sum() / v.sum()) if v.sum() else None

    ic = _arr(intraday, "c") if intraday else np.array([])
    dc = _arr(daily, "c") if daily else np.array([])
    m = macd(ic) if len(ic) else None
    e9 = float(ema(ic, 9)[-1]) if len(ic) else None
    e20 = float(ema(ic, 20)[-1]) if len(ic) else None
    e50d = float(ema(dc, 50)[-1]) if len(dc) >= 50 else None
    e200d = float(ema(dc, 200)[-1]) if len(dc) >= 200 else None
    atr_d = atr(_arr(daily, "h"), _arr(daily, "l"), dc) if len(dc) > 15 else None

    # Relative volume: today's volume vs the 20-day average daily volume.
    day_vol = snap.get("volume") or (sum(b["v"] for b in reg) if reg else None)
    hist = daily[:-1] if daily and today and _et(daily[-1]["t"]).date() == today else daily
    avg20 = float(np.mean([b["v"] for b in hist[-20:]])) if len(hist) >= 5 else None
    rel_vol = round(day_vol / avg20, 2) if day_vol and avg20 else None

    prior = hist[-1] if hist else None
    day_open = snap.get("open") or (reg[0]["o"] if reg else None)

    # Price at the moment the headline came out.
    price_at_news = None
    if news_ts and intraday:
        before = [b for b in intraday if b["t"] <= news_ts]
        price_at_news = before[-1]["c"] if before else None

    trend = None
    if e50d and e200d and last:
        if last > e50d > e200d:
            trend = "Uptrend"
        elif last < e50d < e200d:
            trend = "Downtrend"
        else:
            trend = "Mixed"

    tech = {
        "rsi14": _r(rsi(ic), 1) if len(ic) else None,
        "macd": _r(m[0], 3) if m else None,
        "macd_signal": _r(m[1], 3) if m else None,
        "macd_hist": _r(m[2], 3) if m else None,
        "ema9": _r(e9), "ema20": _r(e20),
        "ema50_d": _r(e50d), "ema200_d": _r(e200d),
        "vwap": _r(vwap), "vwap_dist_pct": _pct(last, vwap),
        "atr14_d": _r(atr_d), "rel_volume": rel_vol, "trend": trend,
    }
    pa = {
        "gap_pct": _pct(day_open, prev_close),
        "premarket_high": _r(max(b["h"] for b in pre)) if pre else None,
        "premarket_low": _r(min(b["l"] for b in pre)) if pre else None,
        "prior_day_high": _r(prior["h"]) if prior else None,
        "prior_day_low": _r(prior["l"]) if prior else None,
        "opening_range_high": _r(max(b["h"] for b in first30)) if first30 else None,
        "opening_range_low": _r(min(b["l"] for b in first30)) if first30 else None,
        "price_at_news": _r(price_at_news),
        "since_news_pct": _pct(last, price_at_news),
    }
    pa["summary"] = describe(last, tech, pa)
    return {
        "price": _r(last),
        "prev_close": _r(prev_close),
        "change": _r(last - prev_close) if last and prev_close else None,
        "change_pct": _pct(last, prev_close),
        "open": _r(day_open),
        "high": _r(snap.get("high")), "low": _r(snap.get("low")),
        "volume": day_vol, "bid": snap.get("bid"), "ask": snap.get("ask"),
        "technicals": tech, "price_action": pa,
    }


def describe(last, t: dict, pa: dict) -> str:
    """A one-line, rule-based read of the price action."""
    if not last:
        return "No recent trades."
    parts = []
    pmh = pa.get("premarket_high")
    if pmh and last > pmh:
        parts.append("trading above the premarket high")
    pdh = pa.get("prior_day_high")
    if pdh and last > pdh:
        parts.append("through the prior-day high")
    pdl = pa.get("prior_day_low")
    if pdl and last < pdl:
        parts.append("below the prior-day low")
    if t.get("vwap"):
        parts.append("holding above VWAP" if last >= t["vwap"] else "below VWAP")
    if t.get("rel_volume"):
        parts.append(f"{t['rel_volume']}× normal volume")
    r = t.get("rsi14")
    if r is not None and (r >= 70 or r <= 30):
        parts.append(f"RSI {'overbought' if r >= 70 else 'oversold'} ({r})")
    if pa.get("since_news_pct") is not None:
        parts.append(f"{pa['since_news_pct']:+.2f}% since the headline")
    s = ", ".join(parts)
    return (s[0].upper() + s[1:] + ".") if s else "Quiet price action."
