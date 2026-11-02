"""Decides whether an incoming story is new or one we've already seen.

Three checks, cheapest first:
  1. the same provider id was ingested before        -> same story, same source
  2. the same canonical URL was seen in the window   -> same story
  3. a near-identical headline (with overlapping tickers, when both have
     tickers) was seen in the window                -> same story from another source
"""
from __future__ import annotations

import hashlib
import re
import time
from collections import deque
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "at", "by", "with",
    "from", "as", "is", "are", "was", "be", "its", "it", "this", "that", "after",
    "says", "said", "new", "inc", "corp", "corporation", "co", "ltd", "plc", "company",
    "announces", "reports", "report", "update", "shares", "stock",
}
_TRACKING = re.compile(r"^(utm_|mc_|cmp|ref|src|feed|rss)", re.I)
_WORD = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")


def canon_url(url: str) -> str:
    if not url:
        return ""
    try:
        p = urlsplit(url.strip())
    except ValueError:
        return url.strip().lower()
    host = p.netloc.lower().removeprefix("www.")
    query = urlencode([(k, v) for k, v in parse_qsl(p.query) if not _TRACKING.match(k)])
    path = p.path.rstrip("/")
    return urlunsplit(("https", host, path, query, ""))


def tokens(headline: str) -> frozenset[str]:
    words = _WORD.findall((headline or "").lower())
    return frozenset(w for w in words if w not in STOPWORDS and len(w) > 1)


def similarity(a: frozenset[str], b: frozenset[str]) -> float:
    """Blend of Jaccard and containment, so a short rewrite of a long headline still matches."""
    if not a or not b:
        return 0.0
    inter = len(a & b)
    jacc = inter / len(a | b)
    contain = inter / min(len(a), len(b))
    return 0.5 * jacc + 0.5 * contain


def raw_id_for(source: str, source_id: str, url: str, headline: str) -> str:
    basis = source_id or canon_url(url) or headline.strip().lower()
    return f"{source}:{hashlib.sha1(basis.encode()).hexdigest()[:20]}"


class Deduper:
    def __init__(self, db, get_settings):
        self.db = db
        self.get_settings = get_settings
        # (news_id, tokens, tickers, first_seen)
        self.recent: deque[tuple[str, frozenset, frozenset, float]] = deque(maxlen=5000)

    def load_recent(self) -> None:
        hours = float(self.get_settings()["dedupe_hours"])
        since = time.time() - hours * 3600
        rows = self.db.query(
            "SELECT id, headline, tickers, first_seen FROM news WHERE first_seen >= ? ORDER BY first_seen",
            (since,),
        )
        self.recent.clear()
        for r in rows:
            self.remember(r["id"], r["headline"], r["tickers"], r["first_seen"])

    def remember(self, news_id: str, headline: str, tickers, first_seen: float) -> None:
        self.recent.append((news_id, tokens(headline), frozenset(tickers or []), first_seen))

    def known_raw(self, raw_id: str) -> bool:
        return self.db.one("SELECT 1 AS x FROM raw_ids WHERE raw_id=?", (raw_id,)) is not None

    def match(self, headline: str, url: str, tickers) -> str | None:
        s = self.get_settings()
        since = time.time() - float(s["dedupe_hours"]) * 3600
        cu = canon_url(url)
        if cu:
            row = self.db.one("SELECT id FROM news WHERE canon_url=? AND first_seen>=?", (cu, since))
            if row:
                return row["id"]
        tk = tokens(headline)
        if len(tk) < 3:
            return None
        threshold = float(s["similarity"])
        tset = frozenset(tickers or [])
        best_id, best = None, 0.0
        for nid, rtk, rtickers, first_seen in reversed(self.recent):
            if first_seen < since:
                break
            if tset and rtickers and not (tset & rtickers):
                continue
            sim = similarity(tk, rtk)
            if sim > best:
                best_id, best = nid, sim
        return best_id if best >= threshold else None
