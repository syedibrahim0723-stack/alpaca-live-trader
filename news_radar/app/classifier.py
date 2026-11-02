"""Labels each story with a category, sentiment, impact and tickers.

The AI path sends batches of new headlines to Claude with a JSON schema, so
the reply always parses. Without an Anthropic key (or if a call fails) the
keyword rules below are used instead.
"""
from __future__ import annotations

import json
import logging
import re

import anthropic

from .models import CATEGORIES, SENTIMENTS, clean_symbols

log = logging.getLogger("news_radar.classifier")

# ── keyword fallback ─────────────────────────────────────────────────────────
KEYWORD_RULES: list[tuple[str, re.Pattern]] = [
    ("Trading Halt", re.compile(r"\b(trading halt|halted|halts trading|luld pause|resumes trading)\b", re.I)),
    ("Offering / Dilution", re.compile(r"\b(offering|private placement|atm program|dilut|warrants?|convertible notes?|shelf registration|424b)\b", re.I)),
    ("Earnings", re.compile(r"\b(earnings|eps|quarter(ly)? results|q[1-4] (results|revenue|profit|loss)|revenue (beat|miss)|beats?|misses|fiscal (year|q[1-4]))\b", re.I)),
    ("Guidance", re.compile(r"\b(guidance|outlook|forecast|raises|lowers|reaffirms|cuts) (its )?(full[- ]year|fy|annual|outlook|guidance)?", re.I)),
    ("Analyst", re.compile(r"\b(upgrade[sd]?|downgrade[sd]?|price target|initiates? coverage|overweight|underweight|outperform|underperform|buy rating|sell rating)\b", re.I)),
    ("M&A", re.compile(r"\b(acquir|acquisition|merger|merge|buyout|takeover|tender offer|to buy|deal to|stake in|go[- ]private)\w*", re.I)),
    ("FDA / Regulatory", re.compile(r"\b(fda|approval|approved|clearance|complete response letter|crl|phase [123i]+|trial|ema|ftc|doj|antitrust|sec charges|regulator)\b", re.I)),
    ("Legal", re.compile(r"\b(lawsuit|class action|sued|settle(ment)?|court|verdict|investigation|subpoena|probe)\b", re.I)),
    ("Insider / SEC", re.compile(r"\b(form 4|13d|13g|8-k|10-q|10-k|insider|director (buys|sells|purchase)|files)\b", re.I)),
    ("Management", re.compile(r"\b(ceo|cfo|coo|chief executive|resigns|steps down|appoint|named (chief|president)|board)\b", re.I)),
    ("Product", re.compile(r"\b(launch|unveil|introduc|partnership|contract|order|agreement|collaborat)\w*", re.I)),
    ("Macro", re.compile(r"\b(cpi|inflation|fomc|fed|powell|rate (cut|hike)|jobs report|payrolls|gdp|treasury|yields?|tariff|pce|ppi)\b", re.I)),
]
BULL = re.compile(r"\b(beat|beats|raises|upgrade|surge|soar|jump|rall|record|approv|wins?|award|strong|tops|exceeds|buyback|outperform|higher)\w*", re.I)
BEAR = re.compile(r"\b(miss|misses|cuts?|lowers|downgrade|plunge|slump|fall|drop|tumble|halt|recall|lawsuit|probe|weak|delay|offering|dilut|resigns|bankrupt|crl|reject|underperform|lower)\w*", re.I)


def keyword_classify(headline: str, summary: str = "") -> dict:
    text = f"{headline} {summary[:400]}"
    category = "Other"
    for cat, pat in KEYWORD_RULES:
        if pat.search(text):
            category = cat
            break
    b, s = len(BULL.findall(headline)), len(BEAR.findall(headline))
    sentiment = "bullish" if b > s else "bearish" if s > b else "neutral"
    impact = 3 if category in ("Trading Halt", "Earnings", "M&A", "FDA / Regulatory", "Guidance", "Offering / Dilution") else 2
    if category in ("Other", "Product"):
        impact = 1
    return {"category": category, "sentiment": sentiment, "impact": impact, "tickers": [], "summary": ""}


# ── Claude classifier ────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""You label US stock-market news for a day trader's live news radar.

For every story you receive, return:
- category: exactly one of {", ".join(CATEGORIES)}. Pick the event the story is about, not the company's industry. Use "Insider / SEC" for regulatory filings (Form 4, 13D/G, 8-K) unless the filing's content clearly fits another category (an 8-K announcing earnings is "Earnings"). "Offering / Dilution" covers stock offerings, warrants, convertibles and ATM programs.
- sentiment: bullish, bearish or neutral for the mentioned stock(s) over the next trading session. Neutral when the story is routine or the direction is unclear.
- impact: an integer 1-5 for how likely it is to move the stock today. 5 = trading halts, FDA decisions, M&A, big earnings surprises or guidance changes; 3 = analyst actions, notable contracts; 1 = conference appearances, routine filings, generic market commentary.
- tickers: US ticker symbols the story is materially about (no exchange prefix). Keep provider-supplied tickers that are relevant; add ones clearly named in the text; drop incidental mentions. Empty list for pure macro stories.
- summary: one plain sentence of at most 20 words saying what happened.

Return one result per input story, echoing its id. Judge only from the text given; do not invent facts."""

CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "category": {"type": "string", "enum": CATEGORIES},
                    "sentiment": {"type": "string", "enum": SENTIMENTS},
                    "impact": {"type": "integer"},
                    "tickers": {"type": "array", "items": {"type": "string"}},
                    "summary": {"type": "string"},
                },
                "required": ["id", "category", "sentiment", "impact", "tickers", "summary"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}

TOPIC_SYSTEM = """You name clusters of stock-market news headlines found by a topic model.
For each cluster you get its top terms and sample headlines. Give it a short, specific label of 2-5 words a trader would recognise (for example "Chip export curbs", "Regional bank earnings", "GLP-1 drug trials"). Avoid generic labels like "Stock news" or "Market update". Return one label per cluster id."""

TOPIC_SCHEMA = {
    "type": "object",
    "properties": {
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "integer"}, "label": {"type": "string"}},
                "required": ["id", "label"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["topics"],
    "additionalProperties": False,
}


class AIClassifier:
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.AsyncAnthropic(api_key=api_key, max_retries=2, timeout=60.0)
        self.model = model

    async def _structured(self, system: str, user: str, schema: dict, max_tokens: int) -> dict | None:
        kwargs = dict(
            model=self.model,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
        )
        try:
            # Server-side fallback: if the model declines, the API retries on a fallback model.
            resp = await self.client.beta.messages.create(
                betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs
            )
        except anthropic.BadRequestError as e:
            log.warning("fallback request rejected (%s); retrying without fallbacks", e.message)
            resp = await self.client.messages.create(**kwargs)
        if resp.stop_reason == "refusal":
            log.warning("classifier request refused")
            return None
        text = next((b.text for b in resp.content if b.type == "text"), "")
        try:
            return json.loads(text)
        except ValueError:
            log.warning("classifier returned non-JSON (stop_reason=%s)", resp.stop_reason)
            return None

    async def classify(self, items: list[dict]) -> dict[str, dict]:
        payload = [
            {
                "id": it["id"],
                "headline": it["headline"],
                "summary": (it.get("summary") or "")[:600],
                "provider_tickers": it.get("tickers") or [],
                "source": it.get("source", ""),
            }
            for it in items
        ]
        data = await self._structured(
            SYSTEM_PROMPT,
            "Classify these stories:\n" + json.dumps(payload, ensure_ascii=False),
            CLASSIFY_SCHEMA,
            max_tokens=600 + 250 * len(items),
        )
        out: dict[str, dict] = {}
        for r in (data or {}).get("items", []):
            out[r["id"]] = {
                "category": r["category"] if r["category"] in CATEGORIES else "Other",
                "sentiment": r["sentiment"] if r["sentiment"] in SENTIMENTS else "neutral",
                "impact": max(1, min(5, int(r.get("impact") or 1))),
                "tickers": clean_symbols(r.get("tickers")),
                "summary": (r.get("summary") or "")[:240],
            }
        return out

    async def label_topics(self, clusters: list[dict]) -> dict[int, str]:
        data = await self._structured(
            TOPIC_SYSTEM,
            json.dumps(clusters, ensure_ascii=False),
            TOPIC_SCHEMA,
            max_tokens=400 + 60 * len(clusters),
        )
        return {int(t["id"]): t["label"][:60] for t in (data or {}).get("topics", [])}
