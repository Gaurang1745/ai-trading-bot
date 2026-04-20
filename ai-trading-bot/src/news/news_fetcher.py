"""
News Fetcher.
Collects headlines from RSS feeds, then summarizes with Haiku.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import feedparser
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# RSS feed sources
RSS_FEEDS = {
    "moneycontrol_market": "https://www.moneycontrol.com/rss/marketreports.xml",
    "moneycontrol_news": "https://www.moneycontrol.com/rss/latestnews.xml",
    "et_markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "livemint": "https://www.livemint.com/rss/markets",
}

# Google News RSS template for stock-specific news
GOOGLE_NEWS_STOCK_URL = (
    "https://news.google.com/rss/search?q={symbol}+stock+NSE&hl=en-IN&gl=IN&ceid=IN:en"
)


class NewsFetcher:
    """
    Fetches news headlines from RSS feeds and optionally summarizes with Haiku.
    """

    def __init__(self, config: dict, claude_client=None):
        self.config = config
        self.claude_client = claude_client
        self._cache: dict[str, list[dict]] = {}
        self._last_fetch: dict[str, datetime] = {}
        self._cache_ttl_minutes = 15
        self._headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    def fetch_market_headlines(self, max_headlines: int = 20) -> list[dict]:
        """
        Fetch top market headlines from all RSS sources.
        Returns list of {source, title, link, published, summary}.
        """
        all_headlines = []

        for source_name, feed_url in RSS_FEEDS.items():
            try:
                entries = self._fetch_feed(feed_url, source_name)
                for entry in entries[:10]:
                    all_headlines.append({
                        "source": source_name,
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "published": self._parse_date(entry),
                        "summary": entry.get("summary", "")[:200],
                    })
            except Exception as e:
                logger.warning(f"Failed to fetch {source_name}: {e}")

        # Sort by recency and deduplicate
        all_headlines.sort(key=lambda x: x["published"], reverse=True)
        all_headlines = self._deduplicate(all_headlines)

        return all_headlines[:max_headlines]

    def fetch_stock_news(self, symbol: str, max_headlines: int = 5) -> list[dict]:
        """Fetch news for a specific stock via Google News RSS."""
        cache_key = f"stock_{symbol}"
        if self._is_cached(cache_key):
            return self._cache[cache_key][:max_headlines]

        url = GOOGLE_NEWS_STOCK_URL.format(symbol=symbol)
        try:
            entries = self._fetch_feed(url, cache_key)
            headlines = []
            for entry in entries[:max_headlines]:
                headlines.append({
                    "source": "google_news",
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "published": self._parse_date(entry),
                    "summary": "",
                })
            self._cache[cache_key] = headlines
            self._last_fetch[cache_key] = datetime.now()
            return headlines
        except Exception as e:
            logger.warning(f"Failed to fetch news for {symbol}: {e}")
            return []

    def summarize_headlines(
        self, headlines: list[dict], max_summaries: int = 10
    ) -> list[dict]:
        """
        Summarize headlines using Haiku for compact, market-relevant summaries.
        Returns headlines with 'ai_summary' field added.
        """
        if not self.claude_client or not headlines:
            return headlines[:max_summaries]

        # Batch headlines for a single Haiku call
        headline_text = "\n".join(
            f"- [{h['source']}] {h['title']}" for h in headlines[:max_summaries]
        )

        prompt = (
            "You are a financial news summarizer. Below are recent Indian stock market "
            "headlines. For each headline, provide a 1-sentence summary focused on the "
            "market impact. Return ONLY a JSON array of strings, one summary per headline, "
            "in the same order. Be concise.\n\n"
            f"Headlines:\n{headline_text}"
        )

        try:
            response = self.claude_client.call_haiku(
                prompt=prompt,
                call_type="NEWS_SUMMARY",
            )
            if response and response.get("summaries"):
                summaries = response["summaries"]
                for i, headline in enumerate(headlines[:max_summaries]):
                    if i < len(summaries):
                        headline["ai_summary"] = summaries[i]
        except Exception as e:
            logger.warning(f"Haiku summarization failed: {e}")

        return headlines[:max_summaries]

    def _fetch_feed(self, url: str, source_name: str) -> list:
        """Fetch and parse an RSS feed."""
        if self._is_cached(source_name):
            return self._cache.get(source_name, [])

        feed = feedparser.parse(url)
        entries = feed.entries if feed.entries else []

        self._cache[source_name] = entries
        self._last_fetch[source_name] = datetime.now()

        return entries

    def _is_cached(self, key: str) -> bool:
        """Check if data is cached and still fresh."""
        if key not in self._last_fetch:
            return False
        age = (datetime.now() - self._last_fetch[key]).total_seconds() / 60
        return age < self._cache_ttl_minutes

    def _parse_date(self, entry) -> str:
        """Parse the published date from an RSS entry."""
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if published:
            try:
                dt = datetime(*published[:6])
                return dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass
        return datetime.now().strftime("%Y-%m-%d %H:%M")

    def _deduplicate(self, headlines: list[dict]) -> list[dict]:
        """Remove duplicate headlines based on title similarity."""
        seen_titles = set()
        unique = []
        for h in headlines:
            title_key = h["title"].lower().strip()[:60]
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique.append(h)
        return unique
