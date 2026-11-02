# Free Primary-Source and RSS Feeds for Market-Moving Stock News (as of Nov 2026)

> Method note: These notes come from web search results gathered on 2026-11-02. The research sandbox's network proxy blocked direct access to sec.gov, nasdaqtrader.com and every feed host, so **no feed URL here was live-tested by this researcher**. Status claims come from official pages surfaced in search plus third-party feed directories (Feeder, wprssaggregator) and GitHub issues dated Oct 2026. Older information carries its date.

## Which free feeds are fastest for market-moving events (filings, halts, press releases)?

### Takeaway
SEC EDGAR is the fastest free primary source. Filings reach the public sec.gov site within about 30–60 seconds of acceptance (2014–2015 measurements), which means polling the `getcurrent` Atom feed or the submissions JSON at 10 req/s or less. The Nasdaq Trader halt RSS updates once a minute and is the only free consolidated halt feed found. Free wire-service RSS (PR Newswire, GlobeNewswire, Business Wire) exists, but none of the three publishes a latency figure, and their paid "full-text newsfeed" products are what media partners receive first.

### Cited Findings

**SEC EDGAR: access rules (applies to all endpoints below)**
- The current maximum request rate is 10 requests/second. The SEC reserves the right to limit request rates to preserve fair access. — [SEC: Accessing EDGAR Data](https://www.sec.gov/os/accessing-edgar-data)
- Automated clients must declare a User-Agent in request headers. The SEC's sample format is company name plus an admin contact email, e.g. `Sample Company Name AdminContact@<sample company domain>.com`. Undeclared automated traffic can be limited, and excessive requests can bring temporary IP blocks. — [SEC: Accessing EDGAR Data](https://www.sec.gov/edgar/searchedgar/accessing-edgar-data.htm)
- Conflict: edgartools docs describe 10/s as a "recommended ceiling" and say the SEC publishes no specific limit, but the SEC's own page states 10 req/s explicitly. Use the SEC page. — [edgartools SEC compliance](https://edgartools.readthedocs.io/en/stable/resources/sec-compliance/) vs [SEC](https://www.sec.gov/os/accessing-edgar-data)

**SEC EDGAR: real-time "Latest Filings" Atom feed (getcurrent)**
- URL pattern: `https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&company=&dateb=&owner=include&start=0&count=100&output=atom`. `type` takes a form type (8-K, 4, SC 13D, etc.). `owner=include|only|exclude` controls whether insider (Forms 3/4/5) filings are included. — [hex.pm sec_recent_filings_rss_feed_parser](https://www.hex.pm/packages/sec_recent_filings_rss_feed_parser/0.0.1); [SEC RSS overview](https://www.sec.gov/files/about/secrss.shtml)
- The SEC says the Latest Filings search can subscribe to all filings or filter by company, CIK, or form type. — [SEC RSS overview](https://www.sec.gov/files/about/secrss.shtml)
- Several commercial scrapers (Apify actors) are built on polling this Atom feed, which suggests it is still active in 2026 (unverified third-party claims). — [Apify SEC EDGAR Current Filings Feed Scraper](https://apify.com/parseforge/sec-edgar-current-feed-scraper?fpr=97nrp4)
- Machine-readable ticker: no. Entries carry the company name and CIK. Map CIK to ticker separately (see Inferences).

**SEC EDGAR: structured-data (XBRL) RSS**
- The XBRL/Inline XBRL RSS feeds update **every ten minutes, Mon–Fri, 6am–10pm EST**. They are slower than getcurrent and only cover XBRL-bearing filings (10-K, 10-Q, some 8-Ks). — [SEC Structured Disclosure RSS Feeds](https://www.sec.gov/structureddata/rss-feeds)

**SEC EDGAR: dissemination latency (applies to 8-K, Form 4, 13D)**
- Per the SEC, acceptance and dissemination "usually takes no longer than two (2) minutes from the receipt of submission by EDGAR." — [SEC PDS dissemination spec](https://www.sec.gov/files/info/edgar/specifications/pds-dissemination-spec070114.pdf)
- EDGAR delivers to the paid Public Dissemination Service (PDS, Tier 1 subscribers) and the SEC website at the same time. — [SEC PDS spec](https://www.sec.gov/info/edgar/pdsnewsubscriber.pdf)
- Measured (2015 study, 4,782 Form 4s): mean time to SEC public posting was **40 s** vs 30 s to Tier 1 subscribers, and 57% reached Tier 1 before public posting. A 2014 measurement found a 36 s median. *Dated 2014–2015.* — [Alpha Architect, "Run EDGAR Run" (Feb 2015)](https://alphaarchitect.com/2015/02/fundamental-investors-following-insider-filings-beware/); [TheCorporateCounsel (Nov 2014)](https://www.thecorporatecounsel.net/blog/2014/11/edgar-dissemination-still-favoring-subscribers.html)

**SEC EDGAR: submissions JSON API and full-text search**
- Submissions JSON lives on `data.sec.gov` (pattern `https://data.sec.gov/submissions/CIK##########.json`, 10-digit zero-padded CIK). Full-text search lives on `efts.sec.gov`. Both are free and need no authentication. — [Arkolith SEC EDGAR API guide](https://arkolith.com/blog/sec-edgar-api-guide)
- The submissions endpoint returns about the 1,000 most recent filings per company, with older ones referenced in separate files. — [Apify aurenic SEC EDGAR scraper](https://apify.com/aurenic/sec-edgar-scraper)
- Full-text search caps results at 10,000 hits, so split queries by date or form. A vendor claims the EFTS index updates in "near real-time — new 8-Ks appear within minutes of SEC acceptance." The vendor claim is not an SEC commitment. — [Apify andrew_avina edgar-fulltext-mcp](https://apify.com/andrew_avina/edgar-fulltext-mcp.md)
- The submissions JSON includes a `tickers` array. Commonly documented, but not confirmed in this session's sources (see Gaps).

**Nasdaq Trader: Trade Halt RSS**
- Free feed with the same halt and pause data as the Trading Halts page, covering **Nasdaq-listed and other exchange-listed securities** (so it includes NYSE-listed halts). — [Nasdaq Trader Trade Halt RSS](https://nasdaqtrader.com/Trader.aspx?id=TradeHaltRSS)
- URL: `http://www.nasdaqtrader.com/rss.aspx?feed=tradehalts`. Optional `haltdate=` / `resumedate=` parameters in `mmddyyyy` format return historical halts. — [Nasdaq Trader Trade Halt RSS](https://nasdaqtrader.com/Trader.aspx?id=TradeHaltRSS)
- Data updates once a minute each trading day, and Nasdaq asks clients **not to query more than once a minute**. — [Nasdaq Trader Trade Halt RSS](https://nasdaqtrader.com/Trader.aspx?id=TradeHaltRSS)
- Use requires accepting a separate Trade Halt RSS Feed Terms & Conditions. — [Nasdaq THRSSFeedTermsCond.pdf](https://m.nasdaqtrader.com/content/administrationsupport/agreementstrading/THRSSFeedTermsCond.pdf)
- Machine-readable ticker: yes. The XML uses an `ndaq:` namespace with per-halt fields (symbol, halt code, times). A developer log notes `?id=tradehalts` fails and `?feed=tradehalts` works. — [gitea SimplyTrading feed_parser.py](https://gitea.com/infrastructure_SC/SimplyTrading/src/branch/main/backend/halt_monitor/feed_parser.py)
- Halt reason codes (T1 news pending, LUDP, etc.) are documented at [Nasdaq Trader Halt Codes](https://nasdaqtrader.com/Trader.aspx?id=TradeHaltCodes).

**NYSE halts**
- No official free public NYSE halt API was found. One source says NYSE has no direct public API and that access runs through licensed vendors. Third-party tools pull NYSE halts from the consolidated Nasdaq Trader feed. — [finfeedapi NYSE API glossary](https://finfeedapi.com/learn/glossary/nyse-api); [glama signal8 get_trading_halts](https://glama.ai/mcp/servers/signal8ai/signal8-mcp/tools/get_trading_halts)

**Press release wires**
- **PR Newswire:** offers an RSS "channel" for its main news feed. — [PR Newswire UK RSS page](https://www.prnewswire.co.uk/rss/). A third-party scraper says per-category feeds were discontinued upstream (single secondary claim, unverified). — [Apify PR Newswire scraper](https://apify.com/crawlerbros/pr-newswire-scraper). The commonly used URL is `https://www.prnewswire.com/rss/news-releases-list.rss`; this URL comes from training knowledge and was not live-tested.
- **GlobeNewswire (Notified):** offers RSS/Atom feeds for custom news pages, with curated feeds by subject, location, industry or **stock exchange**. Search-result pages have a "Subscribe via RSS" option. — [GlobeNewswire press release content](https://www.globenewswire.com/newswire-press-release-content); [GlobeNewswire media partners](https://www.notified.com/GNW-PR/media-partners); [PRISM MediaWire](https://prismmediawire.beehiiv.com/p/utilizing-rss-news-feeds-as-an-alternative-method-for-stock-news-updates-by-prism-mediawire). Releases carry ticker tags that scrapers filter on. — [Apify GlobeNewswire monitor](https://apify.com/scraping_crew/globenewswire)
- **Business Wire:** public RSS at `https://feed.businesswire.com/rss/home/?rss=<encoded-id>` (e.g. `...?rss=G1QFDERJXkJeEF5XWQ==` Retail). Feeder reported it responding normally, check date unclear. — [Feeder Business Wire listing](https://feeder.co/ja/discover/755429e61c/businesswire-com-portal-site-home-news-industry-vnsid-31336). Business Wire's official product for partners is a licensed full-text or headline newsfeed. — [Business Wire media tools](https://secure.businesswire.com/media-journalist-tools)
- **ACCESSWIRE / Newsfile:** no source found confirming a public RSS feed (see Gaps).
- **OTC Markets** news service has an RSS feed (useful for OTC issuers). — [Interactive Brokers page citing OTC RSS](https://www.interactivebrokers.ca/en/index.php?f=31307)

### Inferences
- Speed ranking for free sources: (1) EDGAR getcurrent / submissions JSON, about 30–120 s after acceptance; (2) Nasdaq halt RSS, 1-minute cadence; (3) wire RSS, latency unknown and likely minutes; (4) aggregator RSS (Yahoo, Nasdaq.com, Google News), minutes to tens of minutes because they re-syndicate the wires.
- Many companies file their earnings press release as Exhibit 99.1 to an 8-K (Item 2.02) at about the same time as the wire release. EDGAR 8-K polling can therefore catch earnings nearly as fast as the wire, with a machine-readable CIK.
- A practical EDGAR budget: one getcurrent poll every 2–5 s across a few form types (8-K, 4, SC 13D/G, 6-K, S-1, 424B) is far below 10 req/s and leaves headroom for fetching the filing documents.
- For ticker mapping, SEC publishes `https://www.sec.gov/files/company_tickers.json` (CIK to ticker). This comes from training knowledge and was not verified this session.
- The Nasdaq halt feed is the best free "something is about to happen" signal. Code T1 (news pending) halts usually come before a press release.

### Gaps
- Could not live-test any URL: the sandbox proxy blocked sec.gov, nasdaqtrader.com and all feed hosts.
- No official SEC statement on the getcurrent feed's refresh cadence. It appears to be real-time on each request, but this was not confirmed.
- No current (2024–2026) EDGAR latency measurements. The 30–40 s figures date from 2014–2015.
- No published latency figures for any wire's free RSS feed compared with its paid feed.
- No sources found for ACCESSWIRE (now branded ACCESS Newswire) or Newsfile RSS URLs.
- The submissions JSON `tickers` field and the company_tickers.json URL were not confirmed from search sources.

## Which still work in 2026 and which were shut down?

### Takeaway
Status (third-party reports, Oct 2026): Yahoo Finance's per-ticker headline RSS still works, but its general news RSS returns 404 as of Oct 2026. Reuters RSS has been dead since June 2020. CNBC and MarketWatch (Dow Jones) RSS still exist. Nasdaq.com `rssoutbound` per-symbol feeds exist. Seeking Alpha feeds exist but are restricted to personal, non-commercial use. Google News RSS works but blocks aggressive polling. Government feeds (Fed, FDA, BLS calendar) are active.

### Cited Findings

**Yahoo Finance**
- Per-ticker feed `https://feeds.finance.yahoo.com/rss/2.0/headline?s=TICKER&region=US&lang=en-US` returned current MSFT/NVDA headlines with no key per a GitHub issue dated **Oct 24, 2026**. — [GitHub stock-assistant issue #22](https://github.com/Crooked-Cat-Tail-Software/stock-assistant/issues/22)
- The general feed `finance.yahoo.com/news/rssindex` returns **404**, as do `/rss/topstories` and `/news/rss`, per a PR dated **Oct 31, 2026**. — [GitHub RealMarketFeed PR #12](https://github.com/Phideround/RealMarketFeed/pull/12)
- Feeder could not read Yahoo Finance top stories after Oct 6, 2026. — [Feeder Yahoo Finance](https://feeder.co/discover/c9415058b7/finance-yahoo-com); [Feeder Yahoo RSS KB](https://feeder.co/knowledge-base/rss-content/yahoo-news-rss-feeds/)
- Ticker is machine-readable only through the request parameter. Items carry no structured ticker list.

**Reuters: shut down**
- Reuters discontinued public RSS in **June 2020**. feeds.reuters.com URLs are dead and have not been replaced. The workaround is Google News RSS with `site:reuters.com`. — [Feeder Reuters RSS KB](https://feeder.co/knowledge-base/rss-content/reuters-rss-feeds/); [FiveFilters forum](https://forum.fivefilters.org/t/reuters-rss-feeds-are-down/1152); [Tildes thread](https://tildes.net/~tech/pwe/reuters_removes_rss_feeds)

**CNBC: works**
- Top News feed: `https://www.cnbc.com/id/100003114/device/rss/rss.html`, checked by Feeder on **Oct 3, 2026**. Section feeds swap in the section ID. Some feeds use `https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=<id>`. — [Feeder CNBC RSS KB](https://feeder.co/knowledge-base/rss-content/cnbc-rss-feeds/)

**MarketWatch (Dow Jones): works**
- Legacy `feeds.marketwatch.com/marketwatch/topstories` redirects to `https://feeds.content.dowjones.io/public/rss/mw_topstories`. Feeds are Dow Jones-copyrighted and for personal, non-commercial use. — [Feeder finance news RSS KB](https://feeder.co/knowledge-base/rss-content/finance-news-rss-feeds/)

**Nasdaq.com: works**
- Per-symbol: `https://www.nasdaq.com/feed/rssoutbound?symbol=NVDA`. Per-category: `https://www.nasdaq.com/feed/rssoutbound?category=Markets` (or Commodities, etc.). — [Feeder nasdaq.com listing](https://feeder.co/vi/discover/site/nasdaq.com); [Nasdaq RSS Feeds page](https://www.nasdaq.com/nasdaq-RSS-Feeds)

**Seeking Alpha: works, restricted**
- Main feed `https://seekingalpha.com/feed.xml`. Per-ticker `https://seekingalpha.com/api/sa/combined/AAPL.xml`. Author feeds `seekingalpha.com/author/<slug>.xml`. The feed files state use is limited to **personal, non-commercial use**. — [Feeder finance news RSS KB](https://feeder.co/knowledge-base/rss-content/finance-news-rss-feeds/); [Seeking Alpha author feed](https://seekingalpha.com/author/catalyst-investor.xml)

**Google News RSS: works, throttled**
- Search feeds work even though Google removed the visible RSS links. Time operators `when:1h`, `when:24h`, `when:7d` are supported. Pattern: `https://news.google.com/rss/search?q=<query>+when:1h&hl=en-US&gl=US&ceid=US:en`. — [Codewords Google News RSS guide (May 18, 2026)](https://www.codewords.ai/blog/google-news-rss); [Feeder Reuters KB (example URL)](https://feeder.co/knowledge-base/rss-content/reuters-rss-feeds/)
- Users report 503 / "automated access" blocks under frequent polling. A community suggestion is 15–30 min intervals (anecdotal, not an official limit). — [Make.com community thread](https://community.make.com/t/google-rss-feed-blocked-503-error-automated-access-blocked-any-workarounds/110931)

**Government / macro: active**
- **Federal Reserve:** feed index at `https://www.federalreserve.gov/feeds`, with "All Press Releases" and category feeds such as `https://www.federalreserve.gov/feeds/press_other.xml` and `press_orders.xml`. `press_all.xml` was not directly confirmed. — [federalreserve.gov/feeds](https://federalreserve.gov/feeds); [press_other.xml](https://www.federalreserve.gov/feeds/press_other.xml)
- **Regional Fed / research:** RSS from the Atlanta, Dallas, Chicago and St. Louis Feds, plus Fed in Print. — [Atlanta Fed RSS](https://www.atlantafed.org/rss); [St. Louis Fed RSS](https://www.stlouisfed.org/rss); [Fed in Print RSS](https://fedinprint.org/rss)
- **FDA:** press releases at `https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml`. "What's New: Drugs" (approvals, safety warnings, shortages) at `https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/drugs/rss.xml`. There is no dedicated approvals-only official feed. A third-party approvals feed exists at quantisnow.com/rss/fda. — [newsloth FDA RSS](https://newsloth.com/popular-rss-feeds/fda-rss-feeds); [thenote.app FDA drugs feed](https://thenote.app/post/en/rss-fda-gov-whats-new-drugs-4f15cloikj); [Quantisnow FDA RSS](https://www.quantisnow.com/rss/fda)
- **BLS:** release calendar ICS at `https://www.bls.gov/schedule/news_release/bls.ics`, updated usually at least a week before scheduled releases. Monthly schedule pages: `https://www.bls.gov/schedule/YYYY/MM_sched.htm`. Release dates shifted after the **2025 government shutdown**, and BLS notes dates are subject to change. — [BLS schedule Jan 2026](https://www.bls.gov/schedule/2026/01_sched_list.htm); [BLS schedule Nov 2025](https://www.bls.gov/schedule/2025/11_sched.htm)

**Finviz**
- The news page (`finviz.com/news.ashx`) has no RSS. The unofficial finviz Python library states that scraping "is against their Terms of Service and robots.txt." Free quotes are delayed 15 min (Nasdaq) or 20 min (NYSE/AMEX). — [GitHub major/finviz](https://github.com/major/finviz); [dev.co Finviz overview](https://dev.co/databases/open-source/finviz)

**Other directories**
- wprssaggregator keeps a list of "111 tested feeds (2026)" that is useful for re-verification. — [wprssaggregator News RSS Feeds That Still Work (2026)](https://www.wprssaggregator.com/news-rss-feeds/)
- Feedspot lists 35 stock market news RSS feeds. — [Feedspot](https://rss.feedspot.com/stock_market_news_rss_feeds)

### Inferences
- Yahoo's general feeds died in Oct 2026 while the per-ticker feeds still work, so Yahoo is visibly winding down RSS. Treat per-ticker Yahoo as fragile and build a fallback such as Nasdaq.com `rssoutbound?symbol=`.
- Aggregator feeds (Yahoo, Nasdaq.com, Google News, Seeking Alpha) mostly republish wire releases and their own articles. They help with coverage and dedup, not speed.
- Wire RSS plus EDGAR covers most primary corporate news. Media RSS (CNBC, MarketWatch) is commentary and secondary reporting.

### Gaps
- No sources were found this session on: BEA RSS/calendar (likely `apps.bea.gov/rss/rss.xml` and a release schedule page, unverified); Treasury press-release feed (home.treasury.gov); Investing.com RSS status (`investing.com/rss/news_*.rss`, unverified, and Investing.com is known to be bot-protected); Benzinga free feeds; company IR RSS (many IR sites on Q4/Notified/GCS platforms expose `/rss` news feeds, but this was not confirmed).
- No confirmation of PR Newswire's exact current RSS URL or whether category feeds still exist.
- CNBC and MarketWatch status rests on a single aggregator check dated Oct 3, 2026.

## Legal/terms considerations for automated polling

### Takeaway
Government sources (SEC, Fed, FDA, BLS) are public domain and can be polled freely within their fair-access rules: the SEC requires a declared User-Agent and at most 10 req/s. Nasdaq's halt RSS needs acceptance of its terms and at most 1 request/min. Media and aggregator RSS (Dow Jones/MarketWatch, Seeking Alpha) is explicitly personal, non-commercial use. Finviz forbids scraping. Google News throttles automated access. A commercial app should rely on government and exchange feeds plus wire RSS for headlines and links, and license anything it redistributes in full text.

### Cited Findings
- SEC: 10 req/s maximum; User-Agent must name the company and give a contact email; undeclared or excessive traffic can be rate-limited or IP-blocked. — [SEC Accessing EDGAR Data](https://www.sec.gov/os/accessing-edgar-data); [SEC (alt URL)](https://www.sec.gov/edgar/searchedgar/accessing-edgar-data.htm)
- Nasdaq halt RSS: query no more than once a minute; subject to a separate Terms & Conditions agreement. — [Nasdaq Trader Trade Halt RSS](https://nasdaqtrader.com/Trader.aspx?id=TradeHaltRSS); [Nasdaq T&C PDF](https://m.nasdaqtrader.com/content/administrationsupport/agreementstrading/THRSSFeedTermsCond.pdf)
- MarketWatch/Dow Jones RSS: copyrighted, personal, non-commercial use. — [Feeder finance news RSS KB](https://feeder.co/knowledge-base/rss-content/finance-news-rss-feeds/)
- Seeking Alpha RSS: limited to personal, non-commercial use. — [Feeder finance news RSS KB](https://feeder.co/knowledge-base/rss-content/finance-news-rss-feeds/)
- Finviz: scraping is against its ToS and robots.txt. — [GitHub major/finviz](https://github.com/major/finviz); [dev.co](https://dev.co/databases/open-source/finviz)
- Google News: no published limit, but automated polling gets 503 blocks. Community advice is 15–30 min intervals with caching and exponential backoff. — [Make.com community](https://community.make.com/t/google-rss-feed-blocked-503-error-automated-access-blocked-any-workarounds/110931); [PyPI google-news-api](https://pypi.org/project/google-news-api/)
- GlobeNewswire's official routes for full content are a Reader Account, media partners, or a custom delivery arrangement. Business Wire licenses full-text and headline newsfeeds to partners. — [GlobeNewswire content page](https://www.globenewswire.com/newswire-press-release-content); [Business Wire media tools](https://secure.businesswire.com/media-journalist-tools)
- Paid real-time EDGAR streams (e.g. sec-api.io) exist for teams that need lower latency or push delivery than polling. — [PyPI sec-api](https://pypi.org/project/sec-api)

### Inferences
- A personal or single-user radar that polls and shows headlines with links back carries low risk. Redistributing full article text, or running a multi-user commercial service on Dow Jones, Seeking Alpha, Yahoo or Finviz content, would probably need licenses.
- Polling etiquette: use conditional GETs (ETag/If-Modified-Since), back off exponentially on 429/503, keep one shared poller per feed rather than one per user, and give every request a descriptive User-Agent (required by the SEC, courteous everywhere).
- Suggested intervals: EDGAR getcurrent every 2–10 s (well under 10 req/s in total); Nasdaq halts 60 s; wire RSS 30–60 s; Yahoo/Nasdaq.com per-ticker 1–5 min, rotated across the watchlist; Google News 15+ min; Fed/FDA/BLS 1–5 min around scheduled releases, using the BLS ICS to schedule bursts.

### Gaps
- The actual text of the Nasdaq Trade Halt RSS T&C (commercial redistribution rights) was not read; the PDF was not fetchable.
- No primary-source ToS text was obtained for PR Newswire, GlobeNewswire, Business Wire, CNBC, Yahoo, Nasdaq.com or Google News RSS regarding commercial or automated use.
