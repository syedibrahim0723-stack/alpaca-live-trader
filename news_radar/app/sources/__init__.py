from .alpaca_news import AlpacaNews
from .base import Source, SourceConfig
from .providers import (
    AlphaVantage,
    AnthropicKey,
    Finnhub,
    Marketaux,
    Massive,
    NasdaqHalts,
    NewsAPI,
    RSSFeeds,
    SECEdgar,
    TickerTick,
    Tiingo,
)

# Order = order on the Sources page.
REGISTRY: dict[str, type[Source]] = {
    cls.id: cls
    for cls in (
        AlpacaNews, AnthropicKey,
        SECEdgar, NasdaqHalts, RSSFeeds, TickerTick, Finnhub,
        Massive, Marketaux, Tiingo, AlphaVantage, NewsAPI,
    )
}

__all__ = ["REGISTRY", "Source", "SourceConfig"]
