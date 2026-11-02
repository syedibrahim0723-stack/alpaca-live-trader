"""REST and RSS news providers. Each one maps its response onto RawItem."""
from __future__ import annotations

import asyncio
import html
import re
import time
from datetime import datetime, timedelta, timezone

import feedparser

from ..models import RawItem, clean_symbols, extract_tickers
from .base import Source, ts_from_iso, ts_from_struct

_TAG = re.compile(r"<[^>]+>")


def strip_html(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAG.sub(" ", s or ""))).strip()


UA = "NewsRadar/1.0 (+https://github.com/)"


# ── Finnhub ──────────────────────────────────────────────────────────────────
class Finnhub(Source):
    id = "finnhub"
    name = "Finnhub"
    kind = "Market news + company news for watchlist tickers"
    default_poll = 30
    limit_hint = "Free: 60 calls/min, personal use · Premium adds a news WebSocket"
    signup_url = "https://finnhub.io/register"

    async def fetch(self, http) -> list[RawItem]:
        base, tok = "https://finnhub.io/api/v1", self.cfg.api_key
        r = await http.get(f"{base}/news", params={"category": "general", "token": tok})
        r.raise_for_status()
        rows = list(r.json() or [])
        today = datetime.now(timezone.utc).date()
        for sym in self.watchlist()[:25]:
            rr = await http.get(f"{base}/company-news", params={
                "symbol": sym, "from": str(today - timedelta(days=1)), "to": str(today), "token": tok})
            if rr.status_code == 200:
                for a in rr.json() or []:
                    a.setdefault("related", sym)
                    rows.append(a)
        return [
            RawItem(source=self.id, source_id=str(a.get("id", "")), headline=a.get("headline", ""),
                    summary=a.get("summary", ""), url=a.get("url", ""),
                    published_at=float(a.get("datetime") or time.time()),
                    tickers=clean_symbols((a.get("related") or "").split(",")),
                    publisher=a.get("source", ""))
            for a in rows if a.get("headline")
        ]


# ── TickerTick ───────────────────────────────────────────────────────────────
class TickerTick(Source):
    id = "tickertick"
    name = "TickerTick"
    kind = "Free ticker-tagged news aggregator"
    needs_key = False
    default_poll = 30
    min_poll = 7
    limit_hint = "Free incl. commercial use · 10 requests/min per IP"
    signup_url = "https://github.com/hczhu/TickerTick-API"

    async def fetch(self, http) -> list[RawItem]:
        wl = [s.lower() for s in self.watchlist()[:20]]
        q = f"(or {' '.join('tt:' + s for s in wl)})" if wl else "T:curated"
        r = await http.get("https://api.tickertick.com/feed", params={"q": q, "n": 50})
        r.raise_for_status()
        return [
            RawItem(source=self.id, source_id=str(s.get("id", "")), headline=s.get("title", ""),
                    summary=s.get("description", "") or "", url=s.get("url", ""),
                    published_at=(s.get("time") or time.time() * 1000) / 1000,
                    tickers=clean_symbols(s.get("tags")), publisher=s.get("site", ""))
            for s in (r.json() or {}).get("stories", []) if s.get("title")
        ]


# ── Marketaux ────────────────────────────────────────────────────────────────
class Marketaux(Source):
    id = "marketaux"
    name = "Marketaux"
    kind = "News with per-ticker sentiment scores"
    default_poll = 900
    limit_hint = "Free: 100 requests/day, 3 articles per request"
    signup_url = "https://www.marketaux.com/register"

    async def fetch(self, http) -> list[RawItem]:
        limit = 3 if self.cfg.plan == "Free" else 50
        r = await http.get("https://api.marketaux.com/v1/news/all", params={
            "api_token": self.cfg.api_key, "countries": "us", "filter_entities": "true",
            "language": "en", "limit": limit})
        r.raise_for_status()
        out = []
        for a in (r.json() or {}).get("data", []):
            ents = a.get("entities") or []
            score = sum(e.get("sentiment_score") or 0 for e in ents) / len(ents) if ents else 0
            out.append(RawItem(
                source=self.id, source_id=a.get("uuid", ""), headline=a.get("title", ""),
                summary=a.get("description", "") or "", url=a.get("url", ""),
                published_at=ts_from_iso(a.get("published_at")),
                tickers=clean_symbols(e.get("symbol") for e in ents), publisher=a.get("source", ""),
                provider_sentiment="bullish" if score > 0.15 else "bearish" if score < -0.15 else "neutral"))
        return out


# ── Massive (formerly Polygon.io) ────────────────────────────────────────────
class Massive(Source):
    id = "massive"
    name = "Massive (Polygon.io)"
    kind = "Ticker news with per-ticker sentiment"
    default_poll = 60
    min_poll = 12
    limit_hint = "Free: 5 calls/min · paid plans from ~$29/mo"
    signup_url = "https://massive.com"

    async def fetch(self, http) -> list[RawItem]:
        r = await http.get("https://api.polygon.io/v2/reference/news", params={
            "order": "desc", "sort": "published_utc", "limit": 50, "apiKey": self.cfg.api_key})
        r.raise_for_status()
        out = []
        for a in (r.json() or {}).get("results", []):
            ins = a.get("insights") or []
            sents = [i.get("sentiment") for i in ins]
            sent = max(set(sents), key=sents.count) if sents else ""
            out.append(RawItem(
                source=self.id, source_id=a.get("id", ""), headline=a.get("title", ""),
                summary=a.get("description", "") or "", url=a.get("article_url", ""),
                published_at=ts_from_iso(a.get("published_utc")), tickers=clean_symbols(a.get("tickers")),
                publisher=(a.get("publisher") or {}).get("name", ""),
                provider_sentiment={"positive": "bullish", "negative": "bearish"}.get(sent, "neutral" if sent else "")))
        return out


# ── Alpha Vantage ────────────────────────────────────────────────────────────
class AlphaVantage(Source):
    id = "alphavantage"
    name = "Alpha Vantage"
    kind = "News + sentiment"
    default_poll = 3600
    limit_hint = "Free: 25 requests/day · paid from ~$50/mo"
    signup_url = "https://www.alphavantage.co/support/#api-key"

    async def fetch(self, http) -> list[RawItem]:
        r = await http.get("https://www.alphavantage.co/query", params={
            "function": "NEWS_SENTIMENT", "sort": "LATEST", "limit": 50, "apikey": self.cfg.api_key})
        r.raise_for_status()
        data = r.json() or {}
        if "feed" not in data:
            raise RuntimeError(data.get("Information") or data.get("Note") or "no feed in response")
        out = []
        for a in data["feed"]:
            try:
                ts = datetime.strptime(a["time_published"], "%Y%m%dT%H%M%S").replace(
                    tzinfo=timezone(timedelta(hours=-5))).timestamp()  # AV publishes US/Eastern
            except (KeyError, ValueError):
                ts = time.time()
            label = (a.get("overall_sentiment_label") or "").lower()
            out.append(RawItem(
                source=self.id, headline=a.get("title", ""), summary=a.get("summary", ""),
                url=a.get("url", ""), published_at=ts, publisher=a.get("source", ""),
                tickers=clean_symbols(t.get("ticker") for t in a.get("ticker_sentiment") or []),
                provider_sentiment="bullish" if "bullish" in label else "bearish" if "bearish" in label else "neutral"))
        return out


# ── Tiingo ───────────────────────────────────────────────────────────────────
class Tiingo(Source):
    id = "tiingo"
    name = "Tiingo News"
    kind = "Curated financial news, ticker-tagged"
    default_poll = 120
    limit_hint = "News needs the Power plan (~$30/mo individual)"
    signup_url = "https://www.tiingo.com/account/api/token"

    async def fetch(self, http) -> list[RawItem]:
        r = await http.get("https://api.tiingo.com/tiingo/news", params={"limit": 50},
                           headers={"Authorization": f"Token {self.cfg.api_key}"})
        r.raise_for_status()
        return [
            RawItem(source=self.id, source_id=str(a.get("id", "")), headline=a.get("title", ""),
                    summary=a.get("description", "") or "", url=a.get("url", ""),
                    published_at=ts_from_iso(a.get("publishedDate")), tickers=clean_symbols(a.get("tickers")),
                    publisher=a.get("source", ""))
            for a in r.json() or [] if a.get("title")
        ]


# ── NewsAPI.org ──────────────────────────────────────────────────────────────
class NewsAPI(Source):
    id = "newsapi"
    name = "NewsAPI.org"
    kind = "General headlines (free tier is delayed 24h)"
    default_poll = 900
    limit_hint = "Free: 100 requests/day, 24h delay, dev only · Business $449/mo"
    signup_url = "https://newsapi.org/register"

    async def fetch(self, http) -> list[RawItem]:
        r = await http.get("https://newsapi.org/v2/everything", params={
            "q": '(stock OR shares OR earnings OR "price target")', "language": "en",
            "sortBy": "publishedAt", "pageSize": 50, "apiKey": self.cfg.api_key})
        r.raise_for_status()
        return [
            RawItem(source=self.id, headline=a.get("title", ""), summary=a.get("description", "") or "",
                    url=a.get("url", ""), published_at=ts_from_iso(a.get("publishedAt")),
                    publisher=(a.get("source") or {}).get("name", ""),
                    tickers=extract_tickers(a.get("title", ""), a.get("description", "") or ""))
            for a in (r.json() or {}).get("articles", []) if a.get("title")
        ]


# ── RSS feeds (press-release wires, regulators, Yahoo per ticker) ────────────
DEFAULT_FEEDS = [
    "https://www.globenewswire.com/RssFeed/orgclass/1/feedTitle/GlobeNewswire%20-%20News%20about%20Public%20Companies",
    "https://www.prnewswire.com/rss/news-releases-list.rss",
    "https://feed.businesswire.com/rss/home/?rss=G1QFDERJXkJeGVtRXw==",
    "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml",
    "https://www.federalreserve.gov/feeds/press_all.xml",
]


class RSSFeeds(Source):
    id = "rss"
    name = "RSS feeds"
    kind = "Press-release wires, FDA, Federal Reserve, Yahoo Finance per watchlist ticker"
    needs_key = False
    default_poll = 60
    default_enabled = True
    limit_hint = "Free · poll no faster than once a minute"
    extra_fields = [
        {"name": "feeds", "label": "Feed URLs (one per line)", "type": "lines", "default": DEFAULT_FEEDS},
        {"name": "yahoo_watchlist", "label": "Add Yahoo Finance feed for each watchlist ticker", "type": "bool", "default": True},
    ]

    def feeds(self) -> list[tuple[str, str | None]]:
        urls = self.cfg.extra.get("feeds") or DEFAULT_FEEDS
        out = [(u, None) for u in urls if u.strip()]
        if self.cfg.extra.get("yahoo_watchlist", True):
            out += [(f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={s}&region=US&lang=en-US", s)
                    for s in self.watchlist()[:25]]
        return out

    async def _one(self, http, url: str, sym: str | None) -> list[RawItem]:
        r = await http.get(url, headers={"User-Agent": UA}, follow_redirects=True)
        r.raise_for_status()
        feed = feedparser.parse(r.content)
        host = re.sub(r"^www\.", "", re.sub(r"^https?://([^/]+).*", r"\1", url))
        out = []
        for e in feed.entries[:60]:
            title = strip_html(e.get("title", ""))
            summary = strip_html(e.get("summary", ""))[:1200]
            tickers = [sym] if sym else []
            tickers += [t for t in extract_tickers(title, summary) if t not in tickers]
            for tag in e.get("tags") or []:  # GlobeNewswire tags e.g. "NASDAQ:ABC"
                m = re.match(r"^(?:NASDAQ|NYSE|NYSE American|AMEX|OTC\w*)\s*:\s*([A-Z.]{1,6})$", tag.get("term", ""))
                if m and m.group(1) not in tickers:
                    tickers.append(m.group(1))
            out.append(RawItem(
                source=self.id, source_id=e.get("id", "") or e.get("link", ""), headline=title,
                summary=summary, url=e.get("link", ""),
                published_at=ts_from_struct(e.get("published_parsed") or e.get("updated_parsed")),
                tickers=clean_symbols(tickers), publisher=feed.feed.get("title", host)[:60]))
        return out

    async def fetch(self, http) -> list[RawItem]:
        results = await asyncio.gather(*[self._one(http, u, s) for u, s in self.feeds()], return_exceptions=True)
        items, errors = [], 0
        for res in results:
            if isinstance(res, Exception):
                errors += 1
            else:
                items += res
        if errors and not items:
            raise RuntimeError(f"all {errors} feeds failed")
        self.status.detail = f"{len(results) - errors}/{len(results)} feeds OK"
        return items


# ── Nasdaq trading halts ─────────────────────────────────────────────────────
class NasdaqHalts(Source):
    id = "halts"
    name = "Nasdaq Trader halts"
    kind = "Trading halts and resumptions (all US exchanges)"
    needs_key = False
    default_poll = 60
    min_poll = 60
    default_enabled = True
    limit_hint = "Free · updates once a minute; Nasdaq asks not to poll faster"

    async def fetch(self, http) -> list[RawItem]:
        r = await http.get("https://www.nasdaqtrader.com/rss.aspx?feed=tradehalts", headers={"User-Agent": UA})
        r.raise_for_status()
        feed = feedparser.parse(r.content)
        out = []
        for e in feed.entries:
            sym = (e.get("ndaq_issuesymbol") or e.get("title") or "").strip().upper()
            name = e.get("ndaq_issuename", "")
            reason = e.get("ndaq_reasoncode", "")
            resume = e.get("ndaq_resumptiontradetime", "")
            date = e.get("ndaq_haltdate", "")
            htime = e.get("ndaq_halttime", "")
            state = f"resumes {resume}" if resume else "halted"
            out.append(RawItem(
                source=self.id, source_id=f"{sym}-{date}-{htime}-{resume}",
                headline=f"Trading halt: {sym} {name} — code {reason}, {state}".strip(),
                summary=strip_html(e.get("summary", "")), url="https://www.nasdaqtrader.com/trader.aspx?id=TradeHalts",
                published_at=ts_from_struct(e.get("published_parsed")), tickers=clean_symbols([sym]),
                publisher="Nasdaq Trader"))
        return out


# ── SEC EDGAR live filings ───────────────────────────────────────────────────
FORM_LABELS = {"8-K": "8-K", "4": "Form 4", "SC 13D": "13D", "SC 13G": "13G", "S-1": "S-1",
               "S-3": "S-3", "424B5": "424B5 prospectus", "6-K": "6-K", "10-Q": "10-Q", "10-K": "10-K"}
_EDGAR_TITLE = re.compile(r"^(?P<form>[^-]+?)\s+-\s+(?P<name>.+?)\s+\((?P<cik>\d{10})\)\s+\((?P<role>[^)]+)\)")


class SECEdgar(Source):
    id = "sec"
    name = "SEC EDGAR"
    kind = "Live filings: 8-K, Form 4, 13D/G, offerings"
    needs_key = False
    default_poll = 60
    min_poll = 20
    default_enabled = True
    limit_hint = "Free · max 10 requests/s · needs a User-Agent with your email (Settings)"
    extra_fields = [
        {"name": "forms", "label": "Form types (one per line)", "type": "lines",
         "default": ["8-K", "4", "SC 13D", "424B5", "S-1"]},
    ]
    _cik_map: dict[str, tuple[str, str]] = {}
    _cik_loaded = 0.0

    def ready(self):
        if not self.ctx.settings().get("sec_user_agent"):
            return False, "set the SEC User-Agent in Settings"
        return True, ""

    async def _load_cik_map(self, http, headers) -> None:
        if self._cik_map and time.time() - SECEdgar._cik_loaded < 86400:
            return
        r = await http.get("https://www.sec.gov/files/company_tickers.json", headers=headers)
        r.raise_for_status()
        SECEdgar._cik_map = {str(v["cik_str"]).zfill(10): (v["ticker"], v["title"]) for v in r.json().values()}
        SECEdgar._cik_loaded = time.time()

    async def fetch(self, http) -> list[RawItem]:
        headers = {"User-Agent": self.ctx.settings().get("sec_user_agent") or UA, "Accept-Encoding": "gzip"}
        await self._load_cik_map(http, headers)
        out: list[RawItem] = []
        forms = self.cfg.extra.get("forms") or ["8-K", "4", "SC 13D", "424B5", "S-1"]
        for form in forms:
            r = await http.get("https://www.sec.gov/cgi-bin/browse-edgar", headers=headers, params={
                "action": "getcurrent", "type": form, "owner": "include", "count": 40, "output": "atom"})
            r.raise_for_status()
            feed = feedparser.parse(r.content)
            for e in feed.entries:
                m = _EDGAR_TITLE.match(e.get("title", ""))
                if not m:
                    continue
                # Form 4s list both the reporting person and the issuer; keep the issuer row.
                if m["role"] == "Reporting":
                    continue
                ticker, _title = self._cik_map.get(m["cik"], ("", ""))
                summary = strip_html(e.get("summary", ""))
                label = FORM_LABELS.get(m["form"].strip(), m["form"].strip())
                items = re.findall(r"Item \d\.\d{2}:?\s*[^I]{0,80}", summary)
                head = f"{label}: {m['name'].title()}" + (f" ({ticker})" if ticker else "")
                if items:
                    head += " — " + "; ".join(i.strip() for i in items[:2])
                out.append(RawItem(
                    source=self.id, source_id=e.get("id", ""), headline=head, summary=summary[:800],
                    url=e.get("link", ""), published_at=ts_from_struct(e.get("updated_parsed")),
                    tickers=[ticker] if ticker else [], publisher="SEC EDGAR"))
            await asyncio.sleep(0.15)
        return out


# ── Anthropic (classifier key, not a news source) ────────────────────────────
class AnthropicKey(Source):
    id = "anthropic"
    name = "Anthropic (Claude AI classifier)"
    kind = "Labels categories, sentiment, impact and topics"
    group = "platform"
    default_enabled = True
    limit_hint = "Billed per token · batches of up to 10 headlines per call"
    signup_url = "https://console.anthropic.com/"

    async def run(self) -> None:  # nothing to poll
        self.status.state, self.status.detail = "ok", "ready"
        while True:
            await asyncio.sleep(3600)

    async def test(self) -> str:
        from ..classifier import AIClassifier

        clf = AIClassifier(self.cfg.api_key, self.ctx.settings().get("ai_model"))
        res = await clf.classify([{"id": "t1", "headline": "ABC Corp beats Q3 EPS estimates, raises full-year guidance",
                                   "tickers": ["ABC"]}])
        r = res.get("t1")
        if not r:
            raise RuntimeError("no result")
        return f"OK · test headline → {r['category']}, {r['sentiment']}, impact {r['impact']}"
