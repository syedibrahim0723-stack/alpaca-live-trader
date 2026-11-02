from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

DEFAULT_SETTINGS: dict = {
    "watchlist": [],            # tickers that get company-news polling, flash + sound
    "new_window_min": 15,       # how long a first-seen story keeps its NEW badge
    "dedupe_hours": 24,         # repeats inside this window merge into the first story
    "similarity": 0.8,          # headline similarity (0-1) needed to call two stories the same
    "classifier": "ai",         # "ai" (Claude) or "keywords"
    "ai_model": "claude-opus-5-5",
    "sec_user_agent": "",       # SEC requires "Company Name contact@email"
    "alpaca_feed": "iex",       # "iex" (free) or "sip" (paid)
    "topic_refresh_min": 10,
}

CATEGORIES = [
    "Trading Halt",
    "Earnings",
    "Guidance",
    "Analyst",
    "M&A",
    "FDA / Regulatory",
    "Legal",
    "Insider / SEC",
    "Offering / Dilution",
    "Product",
    "Management",
    "Macro",
    "Other",
]

SENTIMENTS = ["bullish", "bearish", "neutral"]


@dataclass
class RawItem:
    source: str                     # source id, e.g. "finnhub"
    headline: str
    url: str = ""
    summary: str = ""
    source_id: str = ""             # provider's own id, if any
    published_at: float = field(default_factory=time.time)
    tickers: list[str] = field(default_factory=list)
    publisher: str = ""             # e.g. "Benzinga", "Reuters"
    provider_sentiment: str = ""    # sentiment shipped by the provider, if any


_TICKER_PATTERNS = [
    re.compile(r"\((?:NASDAQ|NYSE|NYSE American|NYSE Arca|AMEX|OTC|OTCQB|OTCQX|CBOE|TSX|TSXV)\s*:\s*([A-Z]{1,5}(?:\.[A-Z])?)\)", re.I),
    re.compile(r"(?<![A-Za-z0-9])\$([A-Z]{1,5})(?![A-Za-z0-9])"),
]


def extract_tickers(*texts: str) -> list[str]:
    found: list[str] = []
    for t in texts:
        if not t:
            continue
        for pat in _TICKER_PATTERNS:
            for m in pat.findall(t):
                sym = m.upper()
                if sym not in found:
                    found.append(sym)
    return found


def clean_symbols(symbols) -> list[str]:
    out: list[str] = []
    for s in symbols or []:
        s = str(s).strip().upper().lstrip("$")
        if s and len(s) <= 6 and s not in out:
            out.append(s)
    return out
