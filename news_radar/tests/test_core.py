import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("NEWS_RADAR_DATA", tempfile.mkdtemp())

from app.classifier import keyword_classify  # noqa: E402
from app.core import Radar  # noqa: E402
from app.db import DB  # noqa: E402
from app.dedupe import canon_url, similarity, tokens  # noqa: E402
from app.models import RawItem, extract_tickers  # noqa: E402
from app.technicals import build_report, ema, rsi  # noqa: E402
from app.topics import TopicModel  # noqa: E402


def test_canon_url_strips_tracking():
    a = canon_url("https://www.example.com/story/1/?utm_source=x&id=5#frag")
    b = canon_url("http://example.com/story/1?id=5")
    assert a == b


def test_headline_similarity():
    a = tokens("ABC Corp beats Q3 EPS estimates, raises full-year revenue guidance")
    b = tokens("ABC beats third-quarter EPS estimates and raises full-year revenue guidance")
    c = tokens("XYZ downgraded to Sell at Big Bank")
    assert similarity(a, b) > 0.7
    assert similarity(a, c) < 0.2


def test_extract_tickers():
    assert extract_tickers("Acme Inc. (NASDAQ: ACME) announces deal", "$XYZ moves") == ["ACME", "XYZ"]


def test_keyword_classify():
    assert keyword_classify("XYZ upgraded to Buy; price target raised")["category"] == "Analyst"
    assert keyword_classify("QRS receives FDA complete response letter")["category"] == "FDA / Regulatory"
    assert keyword_classify("ABC prices $50M public offering")["category"] == "Offering / Dilution"


def test_indicators():
    x = np.linspace(1, 100, 200)
    assert abs(ema(x, 10)[-1] - x[-1]) < 6
    assert rsi(x) == 100.0


def test_build_report_since_news():
    t0 = 1793628000.0  # a weekday 13:00 UTC = 09:00 ET (premarket)
    bars = []
    p = 10.0
    for i in range(120):  # 5-minute bars from 09:00 to 19:00 ET
        p += 0.05 if i > 40 else -0.01
        bars.append({"t": t0 + i * 300, "o": p - 0.02, "h": p + 0.05, "l": p - 0.05, "c": p, "v": 1000 + i})
    daily = [{"t": t0 - 86400 * (300 - i), "o": 9, "h": 10.2, "l": 8.8, "c": 9 + i * 0.003, "v": 50000} for i in range(300)]
    rep = build_report(bars, daily, {"price": bars[-1]["c"], "prev_close": 9.9}, news_ts=bars[40]["t"])
    assert rep["price_action"]["since_news_pct"] > 0
    assert rep["technicals"]["vwap"] is not None
    assert rep["price_action"]["premarket_high"] is not None


def test_topics_fit():
    docs = [f"chip export curbs hit semiconductor makers {i}" for i in range(8)] + \
           [f"regional bank earnings beat deposits {i}" for i in range(8)] + \
           [f"drug trial fda approval biotech {i}" for i in range(8)]
    m = TopicModel()
    fitted = m.fit(docs)
    assert fitted is not None
    W, terms = fitted
    assert W.shape[0] == len(docs)


class _Src:
    id = "test"

    class status:  # noqa: N801
        @staticmethod
        def count(*a, **k):
            pass


def test_ingest_new_then_duplicate():
    db = DB(Path(tempfile.mkdtemp()) / "t.db")
    radar = Radar(db)
    now = time.time()

    async def run():
        first = await radar.ingest(_Src, RawItem(source="alpaca", source_id="1", headline="ABC Corp beats Q3 EPS estimates, raises full-year guidance", url="https://a.com/1", tickers=["ABC"], published_at=now))
        dup = await radar.ingest(_Src, RawItem(source="finnhub", source_id="9", headline="ABC Corp beats Q3 EPS estimates and raises full-year guidance", url="https://b.com/x", tickers=["ABC"], published_at=now))
        again = await radar.ingest(_Src, RawItem(source="alpaca", source_id="1", headline="ABC Corp beats Q3 EPS estimates, raises full-year guidance", url="https://a.com/1", tickers=["ABC"], published_at=now))
        old = await radar.ingest(_Src, RawItem(source="rss", headline="DEF to present at investor conference", url="https://c.com/2", published_at=now - 7200))
        return first, dup, again, old

    first, dup, again, old = asyncio.run(run())
    assert (first, dup, again, old) == (True, False, False, True)
    rows = db.query("SELECT * FROM news ORDER BY first_seen")
    assert len(rows) == 2
    assert rows[0]["sources"] == ["alpaca", "finnhub"]
    assert radar.is_new(rows[0]) is True
    assert radar.is_new(rows[1]) is False   # backfilled 2h-old story is stored, not flagged NEW
