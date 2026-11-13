"""Модуль сбора крипто-новостей (RSS через feedparser) и котировок (CoinGecko API через requests)."""

from __future__ import annotations

import calendar
import html
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests

# Таймаут сетевых запросов согласно AGENTS.md: (connect_timeout, read_timeout)
REQUEST_TIMEOUT: tuple[int, int] = (5, 10)
USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) CryptoMonitorDesktop/1.0"
)

# Популярные бесплатные RSS-ленты крипто-новостей
RSS_FEEDS: dict[str, str] = {
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph": "https://cointelegraph.com/rss",
    "Decrypt": "https://decrypt.co/feed",
}

# Сопоставление тикеров с ID в бесплатном API CoinGecko
COINGECKO_IDS: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "LINK": "chainlink",
    "BNB": "binancecoin",
    "XRP": "ripple",
}

COINGECKO_API_URL: str = "https://api.coingecko.com/api/v3/simple/price"

# Регулярные выражения для быстрой и безопасной очистки HTML
RE_SCRIPT_STYLE = re.compile(
    r"<(script|style|iframe|object|embed)[^>]*>.*?</\1>",
    re.DOTALL | re.IGNORECASE,
)
RE_BLOCK_TAGS = re.compile(r"</?(br|p|div|li|tr|h[1-6])[^>]*>", re.IGNORECASE)
RE_HTML_TAGS = re.compile(r"<[^>]+>")
RE_WHITESPACE = re.compile(r"\s+")


def log_parse_error(source: str, exc: Exception | str) -> None:
    """Обязательный вывод ошибок парсинга в консоль (согласно AGENTS.md)."""
    if isinstance(exc, Exception):
        err_msg = f"{type(exc).__name__}: {exc}"
    else:
        err_msg = str(exc)
    print(f"[PARSER ERROR] {source}: {err_msg}", file=sys.stderr, flush=True)


def clean_html_text(raw_html: str | None, max_length: int = 450) -> str:
    """Очищает текст новости от HTML-тегов, декодирует сущности и убирает лишние пробелы."""
    if not raw_html:
        return ""
    try:
        text = RE_SCRIPT_STYLE.sub(" ", str(raw_html))
        text = RE_BLOCK_TAGS.sub(" ", text)
        text = RE_HTML_TAGS.sub("", text)
        text = html.unescape(text)
        text = RE_WHITESPACE.sub(" ", text).strip()
        if max_length and len(text) > max_length:
            return text[: max_length - 3].rstrip() + "..."
        return text
    except Exception as exc:
        log_parse_error("clean_html_text", exc)
        return ""


def _extract_entry_timestamp(entry: Any) -> float:
    """Извлекает Unix-время публикации из записи feedparser (или текущее время при отсутствии)."""
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed_struct = getattr(entry, attr, None) or entry.get(attr)
        if parsed_struct:
            try:
                return float(calendar.timegm(parsed_struct))
            except Exception as exc:
                log_parse_error("timestamp_parse", exc)
    return time.time()


def fetch_rss_news(feeds: dict[str, str] | None = None, max_per_feed: int = 25) -> list[dict[str, Any]]:
    """Собирает и очищает новости из бесплатных RSS-лент."""
    target_feeds = feeds or RSS_FEEDS
    collected_news: list[dict[str, Any]] = []
    headers = {"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml, */*"}

    for source_name, url in target_feeds.items():
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            parsed_feed = feedparser.parse(response.content)

            if getattr(parsed_feed, "bozo", False) and not getattr(parsed_feed, "entries", None):
                bozo_exc = getattr(parsed_feed, "bozo_exception", "Malformed XML/RSS")
                log_parse_error(f"RSS ({source_name} - {url})", bozo_exc)
                continue

            entries = getattr(parsed_feed, "entries", [])[:max_per_feed]
            for entry in entries:
                raw_title = entry.get("title", "")
                raw_summary = entry.get("summary") or entry.get("description") or ""
                link = (entry.get("link") or "").strip()

                title = clean_html_text(raw_title, max_length=200)
                summary = clean_html_text(raw_summary, max_length=450)
                if not title:
                    continue

                pub_ts = _extract_entry_timestamp(entry)
                pub_iso = datetime.fromtimestamp(pub_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

                collected_news.append(
                    {
                        "source": source_name,
                        "title": title,
                        "summary": summary,
                        "link": link,
                        "published_ts": pub_ts,
                        "published_str": pub_iso,
                    }
                )
        except Exception as exc:
            log_parse_error(f"RSS ({source_name} - {url})", exc)

    return collected_news


def fetch_crypto_prices(coins: list[str] | None = None) -> dict[str, dict[str, float]]:
    """Получает актуальные цены (USD) и изменение за 24ч через бесплатный CoinGecko API."""
    target_coins = [c.upper() for c in (coins or list(COINGECKO_IDS.keys())) if c.upper() in COINGECKO_IDS]
    if not target_coins:
        target_coins = list(COINGECKO_IDS.keys())

    ids_param = ",".join(COINGECKO_IDS[ticker] for ticker in target_coins)
    params = {
        "ids": ids_param,
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    prices: dict[str, dict[str, float]] = {}

    try:
        response = requests.get(
            COINGECKO_API_URL,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()

        for ticker in target_coins:
            cg_id = COINGECKO_IDS[ticker]
            coin_data = payload.get(cg_id, {})
            if "usd" in coin_data:
                prices[ticker] = {
                    "usd": float(coin_data.get("usd", 0.0)),
                    "change_24h": float(coin_data.get("usd_24h_change") or 0.0),
                }
            else:
                log_parse_error(f"CoinGecko ({ticker})", f"Missing 'usd' field in response for '{cg_id}'")
    except Exception as exc:
        log_parse_error(f"CoinGecko API ({COINGECKO_API_URL})", exc)

    return prices


def fetch_all_data(selected_coins: list[str] | None = None) -> dict[str, Any]:
    """Собирает котировки и RSS-новости в единый словарь для последующего кэширования."""
    prices = fetch_crypto_prices(selected_coins)
    news = fetch_rss_news()
    return {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": time.time(),
        "prices": prices,
        "news": news,
    }
