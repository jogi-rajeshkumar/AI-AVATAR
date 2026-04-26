"""Search providers: DuckDuckGo (default) and SerpAPI."""
from __future__ import annotations

import os
import re
import logging
from dataclasses import dataclass
from typing import List

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class SearchProvider:
    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:  # noqa: D102
        raise NotImplementedError


class DuckDuckGoProvider(SearchProvider):
    """Scrape DuckDuckGo HTML results – no API key required."""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; AIAvatarBot/1.0; +https://github.com/jogi-rajeshkumar/AI-AVATAR)"
        )
    }

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        try:
            url = "https://html.duckduckgo.com/html/"
            resp = requests.post(
                url,
                data={"q": query},
                headers=self.HEADERS,
                timeout=10,
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            results: List[SearchResult] = []
            for tag in soup.select(".result__body")[:max_results]:
                title_tag = tag.select_one(".result__a")
                snippet_tag = tag.select_one(".result__snippet")
                if not title_tag:
                    continue
                raw_href = title_tag.get("href", "")
                # DDG wraps links – extract real URL if possible
                match = re.search(r"uddg=([^&]+)", raw_href)
                href = requests.utils.unquote(match.group(1)) if match else raw_href
                results.append(
                    SearchResult(
                        title=title_tag.get_text(strip=True),
                        url=href,
                        snippet=(snippet_tag.get_text(strip=True) if snippet_tag else ""),
                    )
                )
            return results
        except Exception as exc:
            logger.warning("DuckDuckGo search failed: %s", exc)
            return []


class SerpAPIProvider(SearchProvider):
    """Google search results via SerpAPI."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        try:
            resp = requests.get(
                "https://serpapi.com/search",
                params={
                    "q": query,
                    "api_key": self._api_key,
                    "engine": "google",
                    "num": max_results,
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            results: List[SearchResult] = []
            for item in data.get("organic_results", [])[:max_results]:
                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                    )
                )
            return results
        except Exception as exc:
            logger.warning("SerpAPI search failed: %s", exc)
            return []


def get_search_provider() -> SearchProvider:
    key = os.getenv("SERPAPI_API_KEY", "").strip()
    if key:
        logger.info("Using SerpAPI search provider")
        return SerpAPIProvider(key)
    logger.info("Using DuckDuckGo search provider (no key)")
    return DuckDuckGoProvider()
