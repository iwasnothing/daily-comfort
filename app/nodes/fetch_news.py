"""
Node 1 — Fetch hot Hong Kong news.

Uses the SerpApi Google Search with tbm=nws to retrieve today's
trending Hong Kong news headlines and snippets.

The formatted output is an HTML <ul> bullet list with each item
containing the article title (clickable), source name, and a
human-friendly date in Chinese format.
"""

import logging
import re

import serpapi

from app.config import SERPAPI_API_KEY

MAX_RESULTS = 5

# Day-of-week names in Traditional Chinese
_WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def _format_date_human_friendly(date_str: str) -> str:
    """
    Convert a SerpApi datetime string to a human-friendly Chinese date format.

    Examples:
        "Wed, 15 Jul 2026 10:01:40 GMT" → "2026年7月15日 星期三"
        "07/13/2026, 08:08 AM, +0000 UTC" → "2026年7月13日 星期一"
        "2026-07-15" → "2026年7月15日 星期三"

    Returns "未知" for empty/Unknown input, or the original string
    if all parsing attempts fail.
    """
    from datetime import datetime

    if not date_str or date_str == "Unknown":
        return "未知"

    # Pre-process: strip trailing timezone info in two passes.
    # Pass 1: remove timezone name suffixes (e.g. " UTC", " HKT").
    # Pass 2: remove trailing numeric offset (e.g. ", +0000", ", +0800").
    # This handles cases like "07/13/2026, 08:08 AM, +0000 UTC".
    normalized = re.sub(
        r"\s*(?:UTC|HKT|CST|EST|PST|GMT|JST|AEST|AEDT)\s*$", "",
        date_str.strip(),
    )
    normalized = re.sub(
        r",?\s*[+-]\d{4}\s*$", "",
        normalized,
    )

    # Try multiple date formats that SerpApi or other sources may return.
    # Format order: most specific first, fallback to most general.
    date_formats = [
        "%a, %d %b %Y %H:%M:%S",  # "Wed, 15 Jul 2026 10:01:40"
        "%a, %b %d, %Y %I:%M %p",  # "Wed, Jul 15, 2026 10:01 AM"
        "%m/%d/%Y, %I:%M %p",  # "07/13/2026, 08:08 AM"
        "%Y-%m-%d %H:%M:%S",  # "2026-07-15 10:01:40"
        "%m/%d/%Y",  # "07/13/2026"
        "%Y-%m-%d",  # "2026-07-15"
    ]

    for fmt in date_formats:
        try:
            dt = datetime.strptime(normalized, fmt)
            # Use month/day directly (no leading zero) for natural Chinese format
            return f"{dt.year}年{dt.month}月{dt.day}日 {_WEEKDAYS[dt.weekday()]}"
        except ValueError:
            continue

    # Fallback: return the original string if no format matched
    return date_str


def fetch_hot_news(state) -> dict:
    """
    Fetch today's hot news about Hong Kong via SerpApi Google News
    and format it.

    Returns a dict with the new ``hot_news`` key so LangGraph merges
    it into the shared state.
    """
    logger = logging.getLogger(__name__)
    logger.info("Node [fetch_hot_news] — starting SerpApi news search")
    logger.debug("Node [fetch_hot_news] — SerpApi configured with key length=%d", len(SERPAPI_API_KEY) if SERPAPI_API_KEY else 0)

    if not SERPAPI_API_KEY:
        logger.error("Node [fetch_hot_news] — SERPAPI_API_KEY is not set")
        return {"hot_news": "(SerpApi key is not configured.)"}

    try:
        logger.debug("Node [fetch_hot_news] — creating SerpApi client and executing search")
        client = serpapi.Client(api_key=SERPAPI_API_KEY)
        search_params = {
            "engine": "google_news",
            "q": "香港",
            "gl": "hk",
            "tbs": "qdr:d",
            "num": 5
        }
        logger.debug("Node [fetch_hot_news] — SerpApi search params: %s", search_params)
        results = client.search(search_params)

        news_results = results.get("news_results", [])
        logger.info("SerpApi returned %d news articles", len(news_results))
        logger.debug("Node [fetch_hot_news] — SerpApi raw response keys: %s", list(results.keys()))

        if not news_results:
            logger.warning("Node [fetch_hot_news] — no news articles found")
            return {"hot_news": "(No news articles found.)"}

        # Format results into an HTML <ul> bullet list.
        # Each <li> contains the article title (clickable) and a metadata span
        # with source name and human-friendly date, separated by a bullet.
        list_items: list[str] = []
        for article in news_results[:MAX_RESULTS]:
            source_info = article.get("source", {})
            source_name = source_info.get("name", "Unknown") if isinstance(source_info, dict) else str(source_info)
            title = article.get("title", "")
            link = article.get("link", "")
            # Skip articles with missing or empty titles — they are malformed responses.
            if not title or title.strip() == "" or title == "Untitled":
                logger.debug(
                    "Node [fetch_hot_news] — skipping article with missing/invalid title"
                )
                continue
            # Wrap title in an anchor tag if a link is available
            if link:
                title_html = f'<a href="{link}" target="_blank" rel="noopener noreferrer">{title}</a>'
            else:
                title_html = title
            friendly_date = _format_date_human_friendly(article.get("date", ""))
            list_items.append(
                f"<li>{title_html}<br><span class=\"news-meta\">{source_name} · {friendly_date}</span></li>"
            )

        if not list_items:
            logger.warning(
                "Node [fetch_hot_news] — all %d articles had missing/invalid titles, skipping",
                len(news_results),
            )
            return {"hot_news": "(All news articles have missing or invalid titles.)"}

        formatted = f'<ul class="news-list">{"".join(list_items)}</ul>'
        logger.info("Node [fetch_hot_news] — fetched %d articles as HTML bullet list", len(list_items))
        return {"hot_news": formatted}

    except Exception as exc:
        logger.error(
            "Node [fetch_hot_news] — error fetching news: %s", exc,
        )
        return {"hot_news": f"(Error fetching news: {exc})"}
