# News Radar

A standalone app that pulls stock news from many sources, flags what's genuinely new, labels every story with Claude, groups stories into trending topics, and shows Alpaca technicals and price action for the ticker you click.

It runs separately from the live-trader app in the parent folder and has its own dependencies, database and port (8100).

```
 Sources (stream / poll)            Pipeline                         Browser
 ─────────────────────────   ─────────────────────────────   ──────────────────────────
 Alpaca / Benzinga (WS)  ─┐  1. seen this provider id? ──► drop    Live desk  (/)
 SEC EDGAR filings        │  2. same URL in 24h?      ──► merge   ├ news feed, NEW badges
 Nasdaq trading halts     ├─►3. similar headline +     ──► merge   ├ category + topic filters
 RSS: wires, FDA, Fed,    │     shared ticker in 24h?             └ ticker panel: chart,
   Yahoo per ticker       │  4. otherwise NEW story ──► SQLite        technicals, reaction
 TickerTick, Finnhub,     │       │                                Sources & keys (/sources)
 Massive, Marketaux,     ─┘       ├─► Claude classifier (batched)   ├ per-source key, plan,
 Tiingo, Alpha Vantage,           └─► topic model (TF-IDF + NMF,    │ poll rate, test button
 NewsAPI                               labels from Claude)           └ settings
                                                   │
                         WebSocket push  ◄─────────┘
```

## Run it

**Windows, one click:** download `install_news_radar.bat` and double-click it. It downloads the app into `%USERPROFILE%\NewsRadar`, adds a "News Radar" shortcut to the desktop and starts the app. Run it again to update; your keys and data are kept. After that, start the app with the shortcut or `run.bat`. Needs Python 3.10+ with "Add python.exe to PATH" ticked during install.

**Windows, from a clone:** double-click `news_radar\run.bat`.

**macOS / Linux:**

```bash
cd news_radar
./run.sh
```

Then open http://127.0.0.1:8100. `run.sh` creates a virtualenv the first time. Without it:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8100
```

On the **Sources & keys** page:

1. **Alpaca:** paste your key ID and secret. This turns on the Benzinga news stream and the prices behind the technicals panel. The free data plan uses the IEX feed; switch to SIP under Data feeds if you pay for it.
2. **Anthropic:** paste an API key to turn on the AI classifier and topic labels. Without it the app falls back to keyword rules.
3. **SEC User-Agent:** sec.gov requires a contact string like `Jane Doe jane@example.com` before the EDGAR source will run.
4. **Watchlist:** tickers listed here get company-news polling (Finnhub, TickerTick, Yahoo RSS) plus a flash and a beep when a NEW story about them arrives.
5. Enable any other provider, paste its key, choose Free or Paid, and press **Test connection**.

Keys can also come from `.env` (see `.env.example`). Keys entered in the UI are encrypted at rest with a key stored in `data/.master.key`, and the page only ever shows them masked.

The server binds to 127.0.0.1 by default and has no login, so don't expose it to a network as-is.

## How "new" is decided

A story is shown with a **NEW** badge only when all of these hold:

- No source has delivered it before. Matching uses the provider's own id, then the canonical URL (tracking parameters stripped), then headline similarity (Jaccard + containment over normalised words, threshold set on the Sources page). When both stories carry tickers they must share at least one.
- It was published within the NEW window (15 min by default). Stories picked up later, for example from a backfill after a restart, are stored and searchable but not flagged.
- You haven't clicked it yet, and the window hasn't run out.

Repeats from other sources are merged into the first copy ("also on Finnhub, RSS (merged)"). Each source's card counts how many stories it was **first to report** today, which gives you real latency data to decide which paid feeds are worth it.

## Categorisation and topic modelling

- **Categories** (fixed list): Trading Halt, Earnings, Guidance, Analyst, M&A, FDA / Regulatory, Legal, Insider / SEC, Offering / Dilution, Product, Management, Macro, Other.
- **AI classifier:** new stories are batched (up to 10 per call, 1.5 s collection window) and sent to Claude with a JSON schema, so the reply always parses. Each story gets a category, sentiment (bullish / bearish / neutral), an impact score from 1 to 5, cleaned ticker list, and a one-line summary. The default model is `claude-opus-5-5` at low effort, changeable in Settings. Server-side fallback is enabled, so a declined request is retried on a fallback model. Stories older than 3 hours at ingest keep keyword labels to save tokens.
- **Topics:** every 10 minutes (configurable, or "Refresh topics") the last 24h of headlines are vectorised with TF-IDF and factorised with NMF (3–12 topics depending on volume). Claude names each topic from its top terms and sample headlines; without a key the top terms are used. New stories are assigned to a topic as they arrive.

## Ticker panel

Clicking a story loads its first ticker, or type any ticker into the search box. Data comes from Alpaca (snapshot, 5-minute bars, daily bars) and refreshes every 15 s:

- Candles with VWAP, EMA 9, volume and a marker on the bar where the headline landed. Timeframes 1m / 5m / 15m / 1H / 1D.
- RSI(14), MACD(12,26,9), EMA 9/20 intraday, EMA 50/200 daily with trend, distance from VWAP, daily ATR(14), relative volume against the 20-day average.
- Reaction: % move since the headline, gap at the open, premarket high/low, 30-minute opening range, prior-day high/low, and a one-line read of the price action.

## Sources

| Source | Key | Default | Notes |
|---|---|---|---|
| Alpaca (Benzinga) | key + secret | on | WebSocket stream with REST backfill; falls back to polling if the stream drops |
| SEC EDGAR | none (User-Agent) | on | 8-K, Form 4, 13D, 424B5, S-1 by default; CIK mapped to ticker |
| Nasdaq Trader halts | none | on | Polled once a minute as Nasdaq asks |
| RSS feeds | none | on | GlobeNewswire, PR Newswire, Business Wire, FDA, Federal Reserve, plus Yahoo per watchlist ticker; edit the list on the card |
| TickerTick | none | off | Free, commercial use allowed, 10 requests/min |
| Finnhub | yes | off | Market news + company news for the watchlist |
| Massive (Polygon) | yes | off | Ticker news with per-ticker sentiment |
| Marketaux | yes | off | Per-entity sentiment; free tier is 100 requests/day |
| Tiingo | yes | off | Needs a paid plan for news |
| Alpha Vantage | yes | off | 25 requests/day free |
| NewsAPI.org | yes | off | Free tier is 24h delayed |

`docs/news-sources-research.md` is a researched comparison of about 50 news providers: coverage, free limits, late-2026 pricing, latency and which ones are worth adding next. Its notes are in `docs/research/`. Most prices there come from secondary sources, so check them on the vendor's site.

Adding a source means writing one `Source` subclass in `app/sources/` with a `fetch()` that returns `RawItem`s, and adding it to `REGISTRY` in `app/sources/__init__.py`. The Sources page picks it up automatically.

## Tests

```bash
cd news_radar
python -m pytest -q tests
```
