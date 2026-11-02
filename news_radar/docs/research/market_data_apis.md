# Developer-facing market-data / fintech APIs with a stock NEWS endpoint (as of Nov 2026)

> **Method caveat (read first):** In this session WebFetch was blocked by network policy for every provider domain tried (massive.com, finnhub.io, docs.alpaca.markets, tiingo.com, alphavantage.co all failed DNS resolution). So the findings below come from **web-search result snippets** of official docs/pricing pages where possible, and from third-party aggregators otherwise (apicostcalc, qveris.ai, fitgap, nexusfi, multiples.vc, mcp.so and similar). Aggregator pricing is often stale or inconsistent. **Check every price against the provider's live pricing page before deciding.** Where sources conflicted, I list both.

---

## Q1. Per-provider fact sheet (coverage, delivery, free tier, paid pricing, latency, tagging/enrichment, history, terms)

### Takeaway
For a real-time radar, the realistic sources are Alpaca/Benzinga (already integrated; REST plus WebSocket, history from 2015), Massive (formerly Polygon; REST ticker news with per-ticker sentiment since Jul 2024, plus a separate real-time Benzinga feed), Finnhub (free REST company news; WebSocket news is Premium-only; press-release stream is Enterprise-only), and Benzinga direct (REST, WebSocket, webhook; enterprise pricing). Most of the rest are REST-polling APIs with daily quotas, aimed at enrichment (sentiment, entities) rather than low latency.

### Cited Findings

#### Alpaca News API (Benzinga), already in use
- Source is Benzinga ("all news data is currently provided directly by Benzinga"). History goes back to **2015**, with an "average of 130+ news articles per day". — [Alpaca Docs: Historical News Data](https://docs.alpaca.markets/us/docs/historical-news-data)
- Delivery is a REST historical endpoint plus a real-time **WebSocket** at `wss://stream.data.alpaca.markets/v1beta1/news`. The docs say the stream delivers 600–900 articles/headlines per day. That conflicts with the "130+/day" average for history; the two counts may measure different things. — [Alpaca Docs: Historical News Data](https://docs.alpaca.markets/us/docs/historical-news-data); [Alpaca news-api page](https://alpaca.markets/docs/news-api)
- Rate limits at launch: free "with rate limits determined by current Market Data API subscription plans; 200 calls per minute for Free plans and 10,000 calls per minute for Unlimited plans". **This is from the original beta launch blog post (circa 2022). Current limits are unconfirmed.** — [Alpaca blog: Introducing News API](https://alpaca.markets/blog/introducing-news-api-for-real-time-fiancial-news/)
- A forum report of an apparent 2015–2016 article-count drop got a reply that nothing appears missing (possibly a pagination artifact). — [Alpaca forum](https://forum.alpaca.markets/t/historical-news-data-missing-for-2016/13576)
- Articles carry a `symbols` ticker list. Alpaca's tutorial does sentiment with external transformers, which implies no native sentiment field. — [Alpaca Learn: sentiment analysis with News API](https://alpaca.markets/learn/sentiment-analysis-with-news-api-and-transformers/)

#### Polygon.io is now **Massive** (confirmed)
- The rebrand to **Massive** took effect **Oct 30, 2025, 4 PM ET**. `api.polygon.io` "will remain supported for an extended period" alongside `api.massive.com`, and existing keys keep working. — [EIN Presswire: Polygon.io is now Massive](https://www.einpresswire.com/article/863823068/polygon-io-is-now-massive); [FISD](https://fisd.net/polygon-io-is-now-massive); [apicostcalc](https://apicostcalc.com/blog/polygon-massive-rebrand-api-pricing.html)
- **Ticker news** is at `/v2/reference/news`. Sentiment sits in an `insights` array, with a **per-ticker sentiment label plus a one-sentence rationale**. Sentiment data starts **2 July 2024**; older articles have none. — [Massive KB: how far back does news & sentiment go](https://massive.com/knowledge-base/article/how-far-back-does-massives-news-and-sentiment-data-go)
- There is a separate **Benzinga News feed** at `/benzinga/v2/news`: Benzinga newsroom content delivered in real time, with **no sentiment field**. — [Massive KB: what does Massive's Benzinga news feed contain](https://massive.com/knowledge-base/article/what-does-massives-benzinga-news-feed-contain)
- Massive added Benzinga datasets (news, analyst insights/ratings, firm reference data), marked real-time capable (blog dated Feb 25, 2026). — [Massive blog: real-time news & analyst dashboard with Benzinga](https://www.massive.com/blog/build-a-real-time-financial-news-and-analyst-intelligence-dashboard-with-massive-benzinga); [Benzinga video: Why Benzinga teamed up with Massive](https://benzinga.videonest.co/videos/1548172/why-benzinga-teamed-up-with-massive-com-RgiG4F8i55)
- Stock plan pricing (aggregator, conflicting): Basic $0, Starter $29, Developer $79, Advanced $199 /mo — [QVeris guide](https://qveris.ai/zh-cn/guides/polygon-pricing-optimized). Starter $29 unchanged after the rebrand — [apicostcalc](https://apicostcalc.com/blog/polygon-massive-rebrand-api-pricing.html). An older QVeris piece cites Developer at $99 (pre-rebrand). — [QVeris FMP vs Polygon](https://qveris.ai/guides/fmp-vs-polygon-io/)
- **I found no published price for the Benzinga add-on**, and no confirmation of whether it is bundled into stock plans. — (search of massive.com KB/blog turned up none)

#### Finnhub
- Free tier: **60 API calls/min**, US coverage, **50 WebSocket symbols** (the free WebSocket is trades/quotes); company news is listed with **1 year** of history on free. — [NexusFi Finnhub listing](https://nexusfi.com/d/data-providers/finnhub/); [QVeris free stock API comparison](https://qveris.ai/guides/stock-api-free-comparison/)
- Conflict: one comparison table also lists a **300 calls/day** cap on free. — [QVeris comparison](https://qveris.ai/guides/stock-api-free-comparison/?lang=zh)
- Free use is **personal / non-commercial**; monetised apps need a paid plan. — [orthogonal.info: tested 4 free stock APIs](https://orthogonal.info/i-tested-4-free-stock-market-apis-heres-which-one-actually-works-for-side-projects/)
- **WebSocket news:** official docs list a "**News** (Premium)" stream for **US & Canadian** stocks (`subscribe-news`). The **press-release** stream (`subscribe-pr`, global companies) is **Enterprise only**. Both are on `wss://ws.finnhub.io`. — [Finnhub API docs](https://www.finnhub.io/docs/api); [digdigdig3 Rust connector source](https://docs.rs/crate/digdigdig3/0.3.6/source/src/l1/free/finnhub/websocket.rs)
- Paid pricing (secondhand, July 2026 reference): Starter about $50/mo; Premium/Pro about $100–$500+/mo. **Not official.** — [apicostcalc Finnhub](https://apicostcalc.com/finnhub.html)
- Developer report: the free WebSocket sometimes drops without a close frame, so robust reconnect logic is needed. — [orthogonal.info Finnhub webhooks post](https://orthogonal.info/i-built-free-stock-price-alerts-with-finnhub-webhooks-in-30-minutes/)

#### Tiingo News
- Paid plans: **Power $30/mo** (individual) and **Business $50/mo**, where commercial use is "limited to internal business use". Redistribution goes through custom commercial licenses from sales. — [Massive vs Tiingo comparison (cites Tiingo pricing page)](https://massive.com/compare/massive-vs-tiingo.md); [findmymoat](https://www.findmymoat.com/vs/databento-vs-tiingo)
- Conflict on whether the **free plan includes the News API**: one source says no; another lists news among free-plan datasets. — [apis.io Tiingo](https://apis.io/providers/tiingo/); [apievangelist Tiingo](https://providers.apievangelist.com/providers/tiingo/)
- Power limits: 5,000 req/hour and 50,000 req/day (per a third-party MCP server's docs). — [glama.ai MCP listing](https://glama.ai/mcp/servers/uumlnxhn95)
- A QuantConnect forum thread reports a Tiingo news feed not working for live trading (an integration issue, not necessarily the API). — [QuantConnect forum](https://www.quantconnect.com/forum/discussion/17182/tiingo-news-feed-not-working-for-live-trading/)

#### Alpha Vantage `NEWS_SENTIMENT`
- Free key: **25 requests/day** (and 5/min). Premium plans exist for usage above that or for "certain premium API functions". — [Alpha Vantage premium page](https://www.alphavantage.co/premium); [macroption](https://www.macroption.com/alpha-vantage-api-limits/)
- Premium monthly tiers (no daily cap, priced by per-minute rate): **$49.99 (75/min), $99.99 (150/min), $149.99 (300/min), $199.99 (600/min), $249.99 (1,200/min)**. — [agentman.ai Alpha Vantage MCP](https://agentman.ai/agentskills/connections/mcp-server/alpha-vantage); [QVeris AV pricing](https://qveris.ai/guides/alpha-vantage-pricing-alternative/)
- Annual billing is reportedly about 10x monthly (unverified, competitor page). — [QVeris](https://qveris.ai/guides/alpha-vantage-pricing-alternative/)

#### Financial Modeling Prep (FMP)
- Free/Basic: **250 calls/day**, end-of-day data. — [FMP pricing (DE)](https://site.financialmodelingprep.com/de/pricing-plans)
- Starter **$29/mo** ($19/mo annual, 300 calls/min). Premium **$69/mo** ($49/mo annual). Higher tiers go to 750 and 3,000 calls/min. Coupon-URL pages may show promo prices. — [FMP pricing](https://site.financialmodelingprep.com/pricing-plans?couponCode=paul); [FMP pricing (ES)](https://site.financialmodelingprep.com/es/pricing-plans)
- Terms: displaying or redistributing FMP data requires a separate **Data Display and Licensing Agreement**. — [FMP pricing](https://site.financialmodelingprep.com/developer/docs/pricing/jesse)

#### EODHD
- "Corporate Events Calendar & News" package at **$19.99/mo**. All-In-One at **$99.99/mo**: 100,000 calls/day and 1,000 req/min, labeled **personal use**. — [EODHD product page](https://eodhd.com/financial-summary/NEWZ.US)
- The news endpoint takes a ticker filter, and articles reportedly carry **sentiment polarity** (via `/news` and `/sentiments`). This is third-party, not confirmed in EODHD docs. — [Jentic EODHD listing](https://jentic.com/apis/eodhd.com/eodhd)

#### Marketaux
- Free: **100 requests/day, 3 articles per request**. Articles carry entity tags (stocks, crypto, FX symbols) with a **sentiment score from -1 to 1** per entity. — [apis.io Marketaux plans](https://apis.io/plans/marketaux/marketaux-plans/); [freeapihub](https://freeapihub.com/apis/marketaux); [nexusfi](https://nexusfi.com/d/data-providers/marketaux/)
- Paid tiers conflict: Basic $29 (2,500/day), Standard $49, Pro $99, Pro 50K $199 — [apis.io](https://apis.io/plans/marketaux/marketaux-plans/). Another source (dated 2026-05-28) lists Basic $9.99 (10k/month) and Growth $39.99. — [apispine](https://apispine.com/marketaux)

#### StockNewsAPI.com
- Basic **$19.99/mo, 20,000 calls/month** (ticker and general news, source/sentiment filters). Premium **$49.99/mo, 50,000 calls** (adds all-ticker news, top mentions/sentiment, trending headlines, **upgrades/downgrades**, historical data). Business is custom. Trial: **5 days / 100 calls**. — [Fitgap](https://us.fitgap.com/products/stock-news-api); [NexusFi](https://nexusfi.com/d/data-providers/stock-news-api)
- Conflict: another Fitgap listing says "Free version unavailable". G2 shows no pricing. — [Fitgap alt](https://us.fitgap.com/products/016892/stock-news-api); [G2](https://www.g2.com/products/stock-news-api/pricing)

#### Intrinio
- Intrinio launched a **live-stream news API** for US companies (blog, July 2024). The REST company-news endpoint takes ticker, CIK, LEI, or Intrinio ID. — [Intrinio blog: live-stream news API](https://intrinio.com/blog/introducing-intrinios-live-stream-news-api-for-us-companies); [Intrinio US News Basic docs](https://docs.intrinio.com/documentation/product/us-news-basic)
- Pricing: individual tier reported at **$150/mo** (third-party). — [multiples.vc Intrinio](https://multiples.vc/compare/intrinio-api-alternatives/md)

#### Twelve Data
- I found **no news endpoint** documented. The free tier is 800 calls/day and 8/min, with WebSocket prices on paid plans. — [CodeWords blog, May 2026](https://www.codewords.ai/blog/twelve-data-api)

#### Benzinga direct (Benzinga Cloud / Newsfeed)
- Delivery: **REST**, **webhooks** (push), and **WebSocket** streaming (multi-protocol suite press release). — [StreetInsider/PRNewswire](https://www.streetinsider.com/PRNewswire/Benzinga+Expands+News+Delivery+Capabilities+with+Comprehensive+Multi-Protocol+Distribution+Suite/25884064.html)
- Webhook contract: POST to your URL; reply 200/201/202/204 or the event is redelivered; events expire after **24h**; handle within **30s**. — [Benzinga webhook v1 docs](https://docs.benzinga.com/benzinga-apis/webhook-v1)
- WebSocket: token query-param auth, ping every 30–60s, message IDs for dedup after reconnect. Newsfeed stream is "always-on" with example clients at github.com/Benzinga/websocket-feed-examples. — [Benzinga WS overview](https://docs.benzinga.com/ws-reference/overview); [Newsfeed stream v1](https://docs.benzinga.com/benzinga-apis/newsfeed-stream-v1/newsfeed-stream-v1)
- Benzinga's Stock News API also offers pull (API) or push (TCP). — [Benzinga Stock News API](https://www.benzinga.com/apis/stock-news-api/)
- **No public price list found**; pricing goes through sales. — [Benzinga FAQ](https://docs.benzinga.com/introduction/faq)

#### AlphAI (alphai.io), used by makeev/alphai-tui
- `alphai-tui` (v0.35.0, Rust) is a terminal dashboard: live quotes and charts plus **AI-scored financial news** and **SEC Form 4 insider activity** from AlphAI. — [docs.rs alphai-tui](https://docs.rs/alphai-tui)
- Delivery is a **REST API plus a hosted MCP server** at `mcp.alphai.io` (Streamable HTTP, OAuth 2.1, no API key). It exposes 11 tools, including `alphai_news_search`, `alphai_ticker_news`, and `alphai_insider_news`. Docs are at alphai.io/developers and alphai.io/mcp. — [mcpservers.org](https://mcpservers.org/servers/makeev/alphai-mcp); [mcp.so](https://mcp.so/servers/alphai-mcp)
- Free-tier limit **conflicts**: 100 calls/hour vs 100/day vs 20/min plus 100/day. Paid: **Basic $2.99/mo, Pro $9.99/mo**. No price data; it summarizes reporting and gives no buy/sell calls. — [mcpservers.org](https://mcpservers.org/servers/makeev/alphai-mcp); [peerlist](https://peerlist.io/mihailmakeev/project/alphai); [hunted.space](https://hunted.space/product/alphai)

#### Unusual Whales API
- The API offers REST, **WebSocket**, and MCP. WebSocket streams cover option trades, SPX Periscope, and CME futures tape. — [UW pricing (API)](https://unusualwhales.com/pricing?product=api)
- Business tier with WebSocket streaming is **$750/mo**; a Kafka tier is **$3,000/mo**. — [UW enterprise](https://unusualwhales.com/pricing/enterprise)
- Older (May 2025) retail API prices: Trial $50/week, Basic $150/mo, Advanced $375/mo. **Outdated.** — [UW Substack, May 2025](https://unusualwhales.substack.com/p/unusual-whales-api-prices-increasing)
- **No news-headline endpoint details found** in search.

#### TickerTick
- **Free for commercial and non-commercial use**. Rate limit is **10 req/min per IP** (1-minute block if exceeded); DM the maintainer for higher rates. Endpoint: `https://api.tickertick.com/feed?q=z:aapl&n=200`. Covers about 10,000 US tickers plus top startups. REST only. — [TickerTick-API GitHub README](https://github.com/hczhu/TickerTick-API)

#### Yahoo Finance via yfinance (unofficial)
- Not affiliated with Yahoo; it scrapes public endpoints that can change at any time. The Yahoo API is "intended for personal use only". Limits are undocumented (one report of 429s after about 950 tickers). Maintainers recommend `requests_cache` plus rate-limiting. — [yfinance fork README](https://github.com/asafravid/yfinance); [yfinance issue #2128](https://github.com/ranaroussi/yfinance/issues/2128)

#### Nasdaq Data Link
- No relevant news-endpoint source found (see Gaps).

### Inferences
- Massive's `/benzinga/v2/news` and Alpaca's news stream both resell Benzinga. Massive adds a separate, non-Benzinga ticker-news feed with per-ticker sentiment. For an app already on Alpaca, Massive mainly adds that sentiment layer plus analyst ratings, not a new primary source.
- StockNewsAPI's Premium tier ($49.99) is the cheapest listed option that explicitly includes analyst upgrades/downgrades as a news category.
- yfinance is unsuitable for anything commercial or production-grade.

### Gaps
- Official, current pricing pages could not be fetched (network policy). Every price above is from search snippets or aggregators and needs live verification.
- Current Alpaca news rate limits (post-beta) and real-world latency are unconfirmed.
- Massive Benzinga add-on price is not found. I also could not confirm whether Massive's news is WebSocket-streamable or REST-only.
- EODHD news history depth and per-plan news limits; Tiingo news history depth and latency.
- Intrinio news pricing and sources; Unusual Whales news endpoint; Nasdaq Data Link news (likely no meaningful real-time stock news product, but unverified).
- Whether Alpha Vantage `NEWS_SENTIMENT` is free-key accessible (widely assumed, not confirmed in this pass).

---

## Q2. Which have a usable free tier for real-time-ish news, and what exact limits?

### Takeaway
Usable free options, best first: **Alpaca** (already in use; WebSocket plus REST; 200 calls/min on free per the original beta post), **Finnhub** (REST company news, 60 calls/min, 1-year history, non-commercial only), **TickerTick** (10 req/min/IP, commercial use allowed), **Marketaux** (100 req/day × 3 articles, with sentiment). **AlphAI** has a small free tier. **Alpha Vantage** (25/day) and **FMP** (250/day, EOD-focused) are too constrained for a radar.

### Cited Findings
- Alpaca free: 200 calls/min (beta-era figure). — [Alpaca blog](https://alpaca.markets/blog/introducing-news-api-for-real-time-fiancial-news/)
- Finnhub free: 60 calls/min, 1 year of news, personal use only; a 300/day cap is reported in one source. — [NexusFi](https://nexusfi.com/d/data-providers/finnhub/); [QVeris](https://qveris.ai/guides/stock-api-free-comparison/?lang=zh); [orthogonal.info](https://orthogonal.info/i-tested-4-free-stock-market-apis-heres-which-one-actually-works-for-side-projects/)
- TickerTick: 10 req/min/IP, free for commercial use. — [GitHub](https://github.com/hczhu/TickerTick-API)
- Marketaux: 100/day, 3 articles/request. — [apis.io](https://apis.io/plans/marketaux/marketaux-plans/)
- AlphAI: 100 calls/hour or /day (conflicting). — [mcpservers.org](https://mcpservers.org/servers/makeev/alphai-mcp)
- Alpha Vantage: 25/day. — [alphavantage.co/premium](https://www.alphavantage.co/premium)
- FMP: 250/day. — [FMP pricing](https://site.financialmodelingprep.com/de/pricing-plans)
- StockNewsAPI: 5-day/100-call trial only. — [Fitgap](https://us.fitgap.com/products/stock-news-api)

### Inferences
- A free-tier radar could combine Alpaca's WebSocket as the primary low-latency feed with Finnhub REST polling (about one call/sec budget) and TickerTick polling for breadth. Commercial use rules out Finnhub's free tier.

### Gaps
- No measured free-tier latency figures found for any provider.

---

## Q3. Which offer streaming (WebSocket) news, and at what price?

### Takeaway
Confirmed WebSocket news: **Alpaca** (included), **Finnhub** (Premium; press releases Enterprise-only), **Benzinga direct** (WebSocket plus webhook; enterprise-priced), **Intrinio** (live-stream news, launched 2024). Unusual Whales has WebSockets, but news over them is unconfirmed. Massive's Benzinga feed is described as "real time", but I could not confirm it is delivered over WebSocket.

### Cited Findings
- Alpaca: `wss://stream.data.alpaca.markets/v1beta1/news`. — [Alpaca docs](https://docs.alpaca.markets/us/docs/historical-news-data)
- Finnhub: News Premium WebSocket (US/CA); press-release WebSocket Enterprise-only. — [Finnhub docs](https://www.finnhub.io/docs/api)
- Benzinga: REST, webhook, and WebSocket. — [PRNewswire](https://www.streetinsider.com/PRNewswire/Benzinga+Expands+News+Delivery+Capabilities+with+Comprehensive+Multi-Protocol+Distribution+Suite/25884064.html); [webhook docs](https://docs.benzinga.com/benzinga-apis/webhook-v1)
- Intrinio live-stream news API. — [Intrinio blog](https://intrinio.com/blog/introducing-intrinios-live-stream-news-api-for-us-companies)
- Unusual Whales WebSocket at the $750/mo business tier (options/futures flow). — [UW enterprise](https://unusualwhales.com/pricing/enterprise)
- Massive Benzinga feed "delivered in real time" via `/benzinga/v2/news`. — [Massive KB](https://massive.com/knowledge-base/article/what-does-massives-benzinga-news-feed-contain)

### Inferences
- Of the WebSocket-news options, Alpaca is the only one already paid for. Benzinga direct's webhooks would be the only server-push option without a persistent socket.

### Gaps
- Finnhub Premium news WebSocket price; Benzinga and Intrinio streaming prices; whether Massive's news goes over WebSocket.
