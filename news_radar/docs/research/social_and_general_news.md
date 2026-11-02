# Social / Alternative-Data and General-Purpose News APIs for a Real-Time Stock "News Radar" (as of Nov 2, 2026)

Method note: In this session WebFetch could not resolve newsapi.org, docs.x.com, gnews.io or newsdata.io (those hosts are outside the sandbox's allowed network domains). So almost every figure below comes from search-result snippets: either snippets of official pages or 2026 third-party roundups. Third-party price figures are marked "(3rd-party)" and should be checked on the vendors' pages before anyone budgets on them. Anything from the model's background knowledge without a source is under Gaps or Inferences, never under Cited Findings.

## Which providers are worth it for detecting stock-moving news early, and which are too noisy or delayed?

### Takeaway
For early detection, the useful sources are push-style, low-latency feeds with a narrow focus: the X API or xAI Grok X Search for breaking chatter (the app already has xAI), the Truth Social feed for presidential posts (paid Truth API, or a third-party WebSocket), Bluesky Jetstream (free but thin on finance), and Unusual Whales WebSockets (flow, alerts, halts). The general news APIs are mostly poll-based keyword search. Their free tiers are delayed by 12–24 hours or capped at very small volumes, so they are only useful as enrichment or backfill. Reddit aggregators (ApeWisdom, Quiver WSB) give mention counts and momentum, not early news, and they can be manipulated.

### Cited Findings

**X / Twitter API**
- X moved to pay-per-use as the default model in Feb 2026 and dropped the free tier for new developers. Legacy Basic ($200/mo) and Pro ($5,000/mo) remain only for existing subscribers. Legacy Basic plans were reportedly migrated to pay-per-use after Jun 1, 2026, and legacy Pro after Sep 1, 2026 (3rd-party) — [Postproxy](https://www.postproxy.dev/blog/x-api-pricing-2026/); [Gigazine](https://gigazine.net/gsc_news/en/20260209-x-api-pay-per-use); [OpenTweet migration guide, updated Oct 2026](https://opentweet.io/how-to/migrate-x-api-pro-to-pay-per-use)
- Pay-per-use rates: about $0.005 per post read, $0.010 per user/DM/follow resource. Sources disagree on the monthly cap: some say 2M post reads per month, newer guides cite 3M per billing cycle, attributed to X docs. Above the cap you need Enterprise (3rd-party) — [bundle.social, Aug 2026](https://bundle.social/blog/x-api-pricing-2026-costs-limits); [OpenTweet pricing](https://opentweet.io/x-api-pricing); [upload-post](https://www.upload-post.com/x-api-pricing/)
- Enterprise reportedly starts around $42k–$50k/mo (3rd-party, unofficial) — [xpoz.ai](https://www.xpoz.ai/blog/guides/understanding-twitter-api-pricing-tiers-and-alternatives/)

**xAI Grok (X Search / Live Search)**
- Server-side tools (web search, X search, code execution) are reported at $5 per 1,000 calls as of Jul 29, 2026, billed on top of tokens. Grok-4.5 tokens: $2 in / $6 out per 1M tokens. Grok-4.3: $1.25 / $2.50 (3rd-party, citing xAI docs) — [ai-toolbox](https://ai-toolbox.co/grok-models/grok-pricing-plans-api-2026); [eesel.ai](https://www.eesel.ai/en/blog/xai-pricing)
- A change tracker reports that on Sep 21, 2026 X Search switched to per-result billing: $5 per 1,000 posts fetched plus $10 per 1,000 user profiles. This comes from one source and is unconfirmed — [usagepricing.com](https://www.usagepricing.com/blueprint/activity/xai-2026-09-21-x-search-per-result-billing)
- The older "Live Search" pricing was $25 per 1,000 sources, with each source type (Web, X, News, RSS) counted separately. This is older and likely superseded — [usagepricing.com xAI](https://usagepricing.com/blueprint/xai)

**StockTwits**
- I found no official 2026 statement on public API access. The integration vendor OneUp said in Oct 2024 that "Stocktwits has removed their API access" — [OneUp help](https://help.oneupapp.io/en-us/article/does-oneup-support-stocktwits-1fxjlx0/)
- Directories still describe the v2 API: symbol/user/trending streams, OAuth 2.0, and hourly rate limits. Undated — [Jentic](https://jentic.com/apis/stocktwits); [RapidAPI listing](https://rapidapi.com/stocktwits/api/stocktwits/details)
- Financial Modeling Prep's social-sentiment endpoint aggregates Reddit, Yahoo, StockTwits and Twitter at 2 credits per call (Databar listing) — [Databar](https://databar.ai/explore/financial-modeling-prep/social-media-sentiment-for-a-specific-stock)

**Reddit API**
- Free tier: about 100 queries per minute with OAuth, non-commercial only. Commercial use needs manual review and a contract. Commercial pricing is quoted variously as about $0.24 per 1,000 calls, or a roughly $12k minimum; other sources say Reddit does not publish commercial pricing (3rd-party, conflicting) — [Techloy](https://www.techloy.com/reddit-api-pricing-in-2026-complete-guide-for-developers-and-businesses/); [apiserpent](https://apiserpent.com/blog/free-reddit-api); [eseospace](https://eseospace.com/blog/reddit-api-pricing/)
- Some 2026 blogs claim new public API access requests stopped Oct 31, 2026, and one gives a Mar 2027 end for the free tier. Uncorroborated — [Medium "Reddit's API is officially dead in 2026"](https://medium.com/@alex_79882/reddits-api-is-officially-dead-in-2026-here-s-what-i-use-instead-f88ee5b809c8); [socialcrawl](https://www.socialcrawl.dev/blog/reddit-data-api-2026)

**Reddit aggregators**
- ApeWisdom: free, rate-limited REST API with no authentication. Ticker mention counts across r/wallstreetbets, r/stocks and crypto subreddits, with subreddit filtering and pagination. Directory entries warn that the data can be bot-manipulated — [NexusFi](https://nexusfi.com/d/data-providers/ape-wisdom/); [ClawKit skill](https://getclawkit.com/skills/official-stuhorsman-apewisdom)
- Quiver Quantitative: WSB daily-discussion mention data by ticker. Pricing figures conflict: API from $10/mo (older PyPI page); $25/mo Premium; API "Hobbyist" at $30/mo, non-commercial; 30-day trial. Also sold on AWS Marketplace with one month free, and available as a QuantConnect dataset (3rd-party) — [PyPI quiverquant 0.1.17 (old)](https://pypi.org/project/quiverquant/0.1.17/); [FindMyMoat](https://www.findmymoat.com/vs/apewisdom-vs-quiver-quantitative); [AWS Marketplace](https://aws.amazon.com/marketplace/pp/prodview-6fzr5ffwsnyra); [QuantConnect](https://www.quantconnect.com/docs/v2/writing-algorithms/datasets/quiver-quantitative/wallstreetbets)
- Finnhub social sentiment: the `stock_social_sentiment` endpoint returns daily Reddit and Twitter data per ticker. I could not confirm its tier or price — [HF code](https://huggingface.co/spaces/kristada673/roboadvisor/blame/main/finnlp/data_sources/social_media/finnhub_sentiment.py)

**Unusual Whales**
- API from $150/mo ($125 on an annual plan). Historical tiers start around $249/mo. WebSocket channels cover flow, alerts, prices and trading halts, and Kafka is available for high volume. Vendor guide dated Jun 2026 — [Unusual Whales guide](https://unusualwhales.com/guides/best-market-data-api-for-ai-agents)
- Business plans: Startup at $750/mo (160k requests per day, WebSocket streaming); Startup + Kafka at $3,000/mo; custom above that — [UW Enterprise pricing](https://unusualwhales.com/pricing/enterprise)
- May 2025 price change: basic $150/mo, advanced $375/mo (older) — [UW Substack, May 2025](https://unusualwhales.substack.com/p/unusual-whales-api-prices-increasing)
- The official Python client does not support WebSockets — [PyPI](https://pypi.org/project/unusualwhales-python-client/4.2.3)

**Bluesky**
- Jetstream is a simplified JSON alternative to the CBOR/CAR atproto firehose, served over WebSocket (e.g. wss://jetstream2.us-east.bsky.network/subscribe, with a backup at jetstream1.us-west) — [Bluesky docs via Algolia](https://docsearch.algolia.com/mcp/docs/repo/bluesky-social/bsky-docs); [playbooks skill](https://playbooks.com/skills/plurigrid/asi/bluesky-jetstream)
- No paid tier or per-call fee. The per-account API limit is 5,000 points per hour and 35,000 per day. That applies to the API; Jetstream-specific limits were not found — [Blotato](https://www.blotato.com/blog/bluesky-api-pricing)

**Truth Social**
- Trump Media's paid "Truth API" was announced Jul 16, 2026 and launched Aug 1, 2026. It is a low-latency feed (claimed "within milliseconds") of the 10 most influential accounts, including the president's, with an archive back to 2022. Price is undisclosed; the FT reported up to about $100k/mo — [CBS News](https://www.cbsnews.com/news/truth-api-trump-media/); [Arab News](https://www.arabnews.pk/media/truth-social-to-sell-trading-firms-fastest-access-to-trumps-posts-2651269); [Neudata](https://www.neudata.co/blog/truth-api-truth-social-data-feed); [t2online](https://t2online.in/tech/tech-news/truth-social-puts-a--100-000-monthly-price-on-hearing-trump-first/2006967)
- Third-party option: 1322.io streams new truths, retruths and quotes for tracked accounts over WebSocket as JSON, from $250/mo. Real-time only, no backfill — [1322.io](https://1322.io/platforms/truth)

**General news APIs (latency-relevant facts)**
- NewsAPI.org free Developer plan: 24-hour article delay, 1-month search window, 100 requests per day, development and testing only (not staging or production). Business: $449/mo, real-time, about 250k requests per month, 5-year search. Advanced: $1,749/mo — [NewsAPI pricing (official snippet)](https://newsapi.org/pricing); [Geekflare](https://geekflare.com/guides/global-news-api/)
- GNews free tier: 100 requests per day, reported 12-hour delay (one source says 15 minutes, which conflicts), non-commercial. Paid from about €/$84/mo (3rd-party) — [socialcrawl](https://www.socialcrawl.dev/blog/best-google-news-apis-2026); [apiserpent](https://apiserpent.com/blog/free-news-api)
- NewsData.io free tier: 200 credits per day (about 1–10 articles per credit), about 12-hour delay, 48-hour window. Paid reportedly from $199.99/mo (3rd-party) — [Geekflare](https://geekflare.com/guides/global-news-api/); [socialcrawl](https://www.socialcrawl.dev/blog/best-google-news-apis-2026)
- Mediastack free tier: 100 calls per month, non-commercial, delay reported as 30 minutes or 12 hours (conflicting). Paid: $24.99/mo for 10k calls, Professional $99.99, Business $249.99 (3rd-party) — [mediastack pricing](https://mediastack.com/pricing); [GTM Directory](https://thegtmdirectory.com/tools/mediastack)
- TheNewsAPI: $0 plan with 100 requests per day but only 3 articles per request. Basic $19/mo for 2,500 requests per day. Currents API free tier: 250 requests per day, 30-day history, HTTP 429 at the cap with no overage billing, redistribution needs separate terms (3rd-party roundups, about Oct 2026) — [apidog](https://apidog.com/blog/free-news-api/); [dev.to](https://dev.to/hassann/top-10-free-news-apis-for-developers-5fg8)
- GDELT DOC 2.0: free, no key or signup, global coverage. Up to 250 articles per response, about 3-month lookback, no article body text — [gdeltcloud compare](https://gdeltcloud.com/compare/news-apis); [apiserpent](https://apiserpent.com/blog/free-news-api)
- NewsCatcher publishes no prices (contact sales). Event Registry / NewsAPI.ai pricing is plan-based with no dollar figures found. Webz.io is sales-led. Perigon has no pricing found — [G2 NewsCatcher](https://www.g2.com/products/newscatcher-news-api/pricing); [newsapi.ai blog](https://newsapi.ai/blog/best-news-api-comparison-2025); [Geekflare](https://geekflare.com/guides/global-news-api/); [softwarefinder Perigon](https://softwarefinder.com/artificial-intelligence/perigon)
- Webz.io's own guidance says to judge news APIs on coverage, latency, duplicates and entity accuracy — [Webz.io blog](https://webz.io/blog/news-api/how-to-evaluate-a-news-api-before-you-buy-coverage-latency-duplicates-entity-accuracy-and-source-quality/)

### Inferences
- **Highest value per dollar:** xAI X Search, already integrated, at about $5 per 1,000 calls. Polling it per watchlist ticker every few minutes is far cheaper than the raw X API at $0.005 per post read, where 3M reads would cost about $15k. The trade-off is that Grok returns LLM-summarized and sampled results, not a guaranteed complete stream.
- **Raw X API:** only worth it for narrow filtered queries (cashtags on a small watchlist, or specific accounts such as @DeItaone-style headline accounts, the Fed or company IR). At $0.005 per read, broad cashtag streaming gets expensive quickly.
- **Truth Social:** a real market mover (tariff and policy posts). The official API is out of reach for a retail app; the $250/mo third-party WebSocket or simple polling of public profiles is the practical route. Scraping may violate the ToS.
- **Bluesky Jetstream:** free and real-time, but financial discussion there is thin. It is low priority, and treating it as a "free X" is speculative.
- **StockTwits:** treat the official API as effectively closed to new developers (unverified). Get StockTwits sentiment indirectly through FMP or similar aggregators.
- **Reddit:** for a retail app, ApeWisdom (free) for mention-velocity spikes is the pragmatic choice over the Reddit API, which is non-commercial on the free tier and uncertain on the paid side. It is a lagging and hype signal, not early news.
- **General news APIs:** NewsAPI's free tier (24h delay), GNews and NewsData free (about 12h), and Mediastack free (100 per month) are useless for early detection. Among the cheap real-time options, TheNewsAPI Basic at $19/mo is the cheapest paid plan found, though its delay is unconfirmed. GDELT is free but built for broad world-event coverage, not ticker-tagged finance. Finance-specific feeds (Benzinga, Alpaca news, Polygon and similar, covered by other researchers) will beat all of these for stock-moving headlines.

### Gaps
- No primary-source confirmation of X's monthly read cap (2M vs 3M) or the current write prices, because docs.x.com was unreachable.
- xAI's X Search billing after Sep 2026 (per call vs per result) is unconfirmed, and docs.x.ai was not checked.
- No official StockTwits statement on 2026 API access.
- Reddit's commercial price and the claimed Oct 31, 2026 cutoff are unverified.
- Swaggy Stocks: no results found on its API or pricing.
- Finnhub social-sentiment tier and price were not found. From background knowledge, it has historically been a premium endpoint (unverified).
- Perigon, NewsCatcher, Webz.io and Event Registry prices were not found (sales-led). I also have no data on their latency.
- Measured latency figures for any general news API were not found. GDELT's 15-minute update cadence was not confirmed by these searches.
- Cashtag prevalence on Bluesky is unknown.

## What are the exact free-tier limits and the cheapest paid tier for each provider?

### Takeaway
Real free and real-time options: GDELT, Bluesky Jetstream and ApeWisdom (all no-cost), plus Reddit's non-commercial OAuth tier. Cheapest paid tiers found: TheNewsAPI at $19/mo, Mediastack at $24.99/mo, GNews at about $84/mo, Unusual Whales at $150/mo, NewsData.io at $199.99/mo, 1322.io (Truth Social) at $250/mo and NewsAPI.org at $449/mo. X and xAI are usage-billed.

### Cited Findings
| Provider | Free tier | Cheapest paid | Source |
|---|---|---|---|
| X API | None for new devs (since Feb 2026) | Pay-per-use: $0.005/post read; cap 2M or 3M per month (conflicting) | [Postproxy](https://www.postproxy.dev/blog/x-api-pricing-2026/), [bundle.social](https://bundle.social/blog/x-api-pricing-2026-costs-limits) |
| xAI Grok X Search | n/a | $5 per 1k tool calls plus tokens (possibly $5 per 1k posts since Sep 21, 2026) | [ai-toolbox](https://ai-toolbox.co/grok-models/grok-pricing-plans-api-2026), [usagepricing](https://www.usagepricing.com/blueprint/activity/xai-2026-09-21-x-search-per-result-billing) |
| Reddit | ~100 QPM via OAuth, non-commercial | Contract; ~$0.24 per 1k calls (unconfirmed) | [Techloy](https://www.techloy.com/reddit-api-pricing-in-2026-complete-guide-for-developers-and-businesses/) |
| StockTwits | Status unclear; access reportedly removed for some (Oct 2024) | n/a | [OneUp](https://help.oneupapp.io/en-us/article/does-oneup-support-stocktwits-1fxjlx0/) |
| ApeWisdom | Free, no auth, rate-limited | n/a | [NexusFi](https://nexusfi.com/d/data-providers/ape-wisdom/) |
| Quiver Quant | 30-day trial | $10–$30/mo (conflicting; Hobbyist is non-commercial) | [FindMyMoat](https://www.findmymoat.com/vs/apewisdom-vs-quiver-quantitative) |
| Unusual Whales | none found | $150/mo ($125 annual); Startup with WebSockets at $750/mo | [UW guide](https://unusualwhales.com/guides/best-market-data-api-for-ai-agents), [UW enterprise](https://unusualwhales.com/pricing/enterprise) |
| Bluesky | Free; 5k points/hr and 35k/day per account | none | [Blotato](https://www.blotato.com/blog/bluesky-api-pricing) |
| Truth Social | none official | Truth API undisclosed (reportedly up to $100k/mo); 1322.io $250/mo | [Neudata](https://www.neudata.co/blog/truth-api-truth-social-data-feed), [1322.io](https://1322.io/platforms/truth) |
| NewsAPI.org | 100 req/day, 24h delay, dev only | Business $449/mo | [NewsAPI](https://newsapi.org/pricing) |
| GNews | 100 req/day, ~12h delay, non-commercial | ~$84/mo | [socialcrawl](https://www.socialcrawl.dev/blog/best-google-news-apis-2026) |
| NewsData.io | 200 credits/day, ~12h delay | ~$199.99/mo | [Geekflare](https://geekflare.com/guides/global-news-api/) |
| Mediastack | 100 calls/month, non-commercial | $24.99/mo (10k calls) | [GTM Directory](https://thegtmdirectory.com/tools/mediastack) |
| TheNewsAPI | 100 req/day, 3 articles/req | $19/mo (2,500 req/day) | [apidog](https://apidog.com/blog/free-news-api/) |
| Currents | 250 req/day, 30-day history | not found | [apidog](https://apidog.com/blog/free-news-api/) |
| GDELT | Free, no key, 250 articles/response | n/a | [gdeltcloud](https://gdeltcloud.com/compare/news-apis) |
| Webz.io / Perigon / NewsCatcher / Event Registry | not found | Sales-led / not published | [G2](https://www.g2.com/products/newscatcher-news-api/pricing), [Geekflare](https://geekflare.com/guides/global-news-api/) |

### Inferences
- For a retail news radar, a near-zero-cost stack would be: xAI X Search (existing) + ApeWisdom + GDELT + Bluesky Jetstream, with an optional $19/mo TheNewsAPI. For broader real-time headline coverage, a finance-specific feed is a better buy than NewsAPI.org at $449/mo.
- Several free tiers are non-commercial (Reddit, GNews, Mediastack, NewsAPI dev-only, Quiver Hobbyist). Using them in a deployed app, even a personal trading app, risks breaching their terms.

### Gaps
- Exact current paid prices for GNews (EUR vs USD), NewsData.io, Currents, Perigon, NewsCatcher, Event Registry and Webz.io could not be checked against official pages.
- Ticker tagging and sentiment fields per general news API were not confirmed: NewsData.io and Perigon reportedly offer sentiment on higher tiers, and GDELT has tone scores, but none of this was sourced in this session.
- Exact ApeWisdom rate-limit numbers were not found.
