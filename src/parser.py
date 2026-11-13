"""Модуль сбора крипто-новостей (RSS через feedparser), котировок и истории цен за выбранный период."""

from __future__ import annotations

import calendar
from concurrent.futures import ThreadPoolExecutor, as_completed
import html
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus

import feedparser
import requests

# Таймаут сетевых запросов согласно AGENTS.md: (connect_timeout, read_timeout)
REQUEST_TIMEOUT: tuple[int, int] = (5, 10)
USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) CryptoMonitorDesktop/1.0"
)

# Базовые бесплатные RSS-ленты крипто-новостей (свежие новости за 1ч - 24ч)
BASE_RSS_FEEDS: dict[str, str] = {
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph": "https://cointelegraph.com/rss",
    "Decrypt": "https://decrypt.co/feed",
}

# Специализированные RSS-ленты по монетам (содержат новости за неделю и месяц)
COIN_TAG_RSS_FEEDS: dict[str, tuple[str, str]] = {
    "BTC": ("Cointelegraph BTC", "https://cointelegraph.com/rss/tag/bitcoin"),
    "ETH": ("Cointelegraph ETH", "https://cointelegraph.com/rss/tag/ethereum"),
    "SOL": ("Cointelegraph SOL", "https://cointelegraph.com/rss/tag/solana"),
    "LINK": ("Cointelegraph LINK", "https://cointelegraph.com/rss/tag/chainlink"),
    "BNB": ("Cointelegraph BNB", "https://cointelegraph.com/rss/tag/binance"),
    "XRP": ("Cointelegraph XRP", "https://cointelegraph.com/rss/tag/ripple"),
}

# Названия монет для поисковых RSS-запросов за выбранный период
COIN_SEARCH_NAMES: dict[str, str] = {
    "BTC": "Bitcoin BTC",
    "ETH": "Ethereum ETH",
    "SOL": "Solana SOL",
    "LINK": "Chainlink LINK",
    "BNB": "BNB Binance Coin",
    "XRP": "Ripple XRP",
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

# Сопоставление тикеров с торговыми парами в публичном API Binance (для точных графиков цен)
BINANCE_SYMBOLS: dict[str, str] = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "LINK": "LINKUSDT",
    "BNB": "BNBUSDT",
    "XRP": "XRPUSDT",
}

COINGECKO_API_URL: str = "https://api.coingecko.com/api/v3/simple/price"
BINANCE_KLINES_URL: str = "https://api.binance.com/api/v3/klines"
BINANCE_TICKER_24H_URL: str = "https://api.binance.com/api/v3/ticker/24hr"

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


def _timeframe_to_google_when(timeframe: str) -> str:
    """Преобразует выбранный Timeline в параметр времени Google News RSS (when:...)."""
    tf = (timeframe or "").lower()
    if "1 час" in tf or tf == "1h":
        return "1h"
    if "6 час" in tf or tf == "6h":
        return "6h"
    if "3 дн" in tf or tf == "3d":
        return "3d"
    if "недел" in tf or "7 дн" in tf or tf == "7d":
        return "7d"
    if "месяц" in tf or "30 дн" in tf or tf == "30d":
        return "30d"
    return "1d"


def _build_dynamic_feeds(
    selected_coins: list[str] | None,
    timeframe: str,
) -> dict[str, str]:
    """Формирует список RSS-источников с учетом выбранных монет и временного диапазона."""
    feeds: dict[str, str] = dict(BASE_RSS_FEEDS)
    coins = [c.strip().upper() for c in (selected_coins or list(COINGECKO_IDS.keys())) if c.strip()]
    when_tag = _timeframe_to_google_when(timeframe)

    for ticker in coins:
        # Добавляем тематическую ленту Cointelegraph по конкретной монете (охватывает неделю и месяц)
        if ticker in COIN_TAG_RSS_FEEDS:
            src_name, url = COIN_TAG_RSS_FEEDS[ticker]
            feeds[src_name] = url

        # Добавляем Google News RSS с точным фильтром времени when:<timeframe>
        coin_query = COIN_SEARCH_NAMES.get(ticker, ticker)
        encoded_q = quote_plus(f"{coin_query} crypto when:{when_tag}")
        feeds[f"GoogleNews ({ticker})"] = (
            f"https://news.google.com/rss/search?q={encoded_q}&hl=en-US&gl=US&ceid=US:en"
        )

    return feeds


def _fetch_single_feed(source_name: str, url: str, max_per_feed: int) -> list[dict[str, Any]]:
    """Загружает и разбирает одну RSS-ленту."""
    items: list[dict[str, Any]] = []
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        parsed_feed = feedparser.parse(response.content)

        if getattr(parsed_feed, "bozo", False) and not getattr(parsed_feed, "entries", None):
            bozo_exc = getattr(parsed_feed, "bozo_exception", "Malformed XML/RSS")
            log_parse_error(f"RSS ({source_name} - {url})", bozo_exc)
            return items

        entries = getattr(parsed_feed, "entries", [])[:max_per_feed]
        for entry in entries:
            raw_title = entry.get("title", "")
            raw_summary = entry.get("summary") or entry.get("description") or ""
            link = (entry.get("link") or "").strip()

            title = clean_html_text(raw_title, max_length=210)
            summary = clean_html_text(raw_summary, max_length=450)
            if not title:
                continue

            # Для Google News часто в summary дублируется заголовок — делаем аккуратную очистку
            if summary and summary.startswith(title[:40]):
                summary = summary[len(title) :].lstrip(" -–—•:")

            pub_ts = _extract_entry_timestamp(entry)
            pub_iso = datetime.fromtimestamp(pub_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

            items.append(
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

    return items


def fetch_rss_news(
    feeds: dict[str, str] | None = None,
    max_per_feed: int = 30,
    selected_coins: list[str] | None = None,
    timeframe: str = "24h",
) -> list[dict[str, Any]]:
    """Параллельно собирает и очищает новости из бесплатных RSS-лент с учетом периода."""
    target_feeds = feeds or _build_dynamic_feeds(selected_coins, timeframe)
    collected_news: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=min(8, max(1, len(target_feeds)))) as executor:
        future_map = {
            executor.submit(_fetch_single_feed, src, url, max_per_feed): src
            for src, url in target_feeds.items()
        }
        for future in as_completed(future_map):
            try:
                collected_news.extend(future.result())
            except Exception as exc:
                log_parse_error(f"RSS Worker ({future_map[future]})", exc)

    return collected_news


def fetch_crypto_prices(coins: list[str] | None = None) -> dict[str, dict[str, float]]:
    """Получает актуальные цены (USD) и изменение за 24ч (CoinGecko API с резервом Binance)."""
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
    except Exception as exc:
        log_parse_error(f"CoinGecko API ({COINGECKO_API_URL})", exc)

    # Добираем недостающие котировки через публичный API Binance 24hr ticker
    missing = [t for t in target_coins if t not in prices and t in BINANCE_SYMBOLS]
    for ticker in missing:
        try:
            resp = requests.get(
                BINANCE_TICKER_24H_URL,
                params={"symbol": BINANCE_SYMBOLS[ticker]},
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            b_data = resp.json()
            prices[ticker] = {
                "usd": float(b_data.get("lastPrice", 0.0)),
                "change_24h": float(b_data.get("priceChangePercent", 0.0)),
            }
        except Exception as exc:
            log_parse_error(f"Binance 24hr Ticker ({ticker})", exc)

    return prices


def _resolve_klines_params(timeframe: str) -> tuple[str, int, int]:
    """
    Возвращает (interval, limit, days) для публичного API свечей Binance и CoinGecko
    в соответствии с выбранным промежутком времени.
    """
    tf = (timeframe or "").lower()
    if "1 час" in tf or tf == "1h":
        return "1m", 60, 1
    if "6 час" in tf or tf == "6h":
        return "5m", 72, 1
    if "3 дн" in tf or tf == "3d":
        return "1h", 72, 3
    if "недел" in tf or "7 дн" in tf or tf == "7d":
        return "2h", 84, 7
    if "месяц" in tf or "30 дн" in tf or tf == "30d":
        return "6h", 120, 30
    return "15m", 96, 1


def _fetch_single_coin_history(
    ticker: str,
    interval: str,
    limit: int,
    days: int,
) -> list[dict[str, float]]:
    """Получает временной ряд цен [{'ts': ..., 'price': ...}, ...] для одной монеты."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    symbol = BINANCE_SYMBOLS.get(ticker)

    # 1. Пробуем быстрый и точный публичный эндпоинт Binance Klines
    if symbol:
        try:
            resp = requests.get(
                BINANCE_KLINES_URL,
                params={"symbol": symbol, "interval": interval, "limit": limit},
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            raw_klines = resp.json()
            if isinstance(raw_klines, list) and raw_klines:
                series: list[dict[str, float]] = []
                for row in raw_klines:
                    # row[0] = open_time (ms), row[4] = close_price
                    series.append(
                        {
                            "ts": float(row[0]) / 1000.0,
                            "price": float(row[4]),
                        }
                    )
                return series
        except Exception as exc:
            log_parse_error(f"Binance Klines ({ticker})", exc)

    # 2. Резервный вариант через CoinGecko market_chart
    cg_id = COINGECKO_IDS.get(ticker)
    if cg_id:
        try:
            url = f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart"
            resp = requests.get(
                url,
                params={"vs_currency": "usd", "days": str(days)},
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            payload = resp.json()
            raw_prices = payload.get("prices", [])
            cutoff = time.time() - (limit * 60 if interval == "1m" else days * 86400)
            series = [
                {"ts": float(p[0]) / 1000.0, "price": float(p[1])}
                for p in raw_prices
                if isinstance(p, list) and len(p) >= 2 and (float(p[0]) / 1000.0) >= cutoff
            ]
            return series
        except Exception as exc:
            log_parse_error(f"CoinGecko MarketChart ({ticker})", exc)

    return []


def fetch_price_history(
    coins: list[str] | None = None,
    timeframe: str = "24h",
) -> dict[str, list[dict[str, float]]]:
    """Параллельно загружает историю цен по выбранным монетам за указанный период."""
    target_coins = [c.upper() for c in (coins or list(COINGECKO_IDS.keys())) if c.upper() in COINGECKO_IDS]
    if not target_coins:
        target_coins = list(COINGECKO_IDS.keys())

    interval, limit, days = _resolve_klines_params(timeframe)
    history: dict[str, list[dict[str, float]]] = {}

    with ThreadPoolExecutor(max_workers=min(6, len(target_coins))) as executor:
        future_map = {
            executor.submit(_fetch_single_coin_history, ticker, interval, limit, days): ticker
            for ticker in target_coins
        }
        for future in as_completed(future_map):
            ticker = future_map[future]
            try:
                pts = future.result()
                if pts:
                    history[ticker] = pts
            except Exception as exc:
                log_parse_error(f"Price History Worker ({ticker})", exc)

    return history


def fetch_all_data(
    selected_coins: list[str] | None = None,
    timeframe: str = "24h",
) -> dict[str, Any]:
    """Собирает котировки, историю цен за период и RSS-новости в единый словарь для кэширования."""
    prices = fetch_crypto_prices(selected_coins)
    price_history = fetch_price_history(selected_coins, timeframe=timeframe)
    news = fetch_rss_news(selected_coins=selected_coins, timeframe=timeframe)

    # Если CoinGecko не вернул текущую цену, берем последнюю точку из истории свечей
    for ticker, series in price_history.items():
        if ticker not in prices and len(series) >= 2:
            first_p = series[0]["price"]
            last_p = series[-1]["price"]
            pct = ((last_p - first_p) / first_p * 100.0) if first_p else 0.0
            prices[ticker] = {"usd": last_p, "change_24h": pct}

    return {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": time.time(),
        "timeframe": timeframe,
        "prices": prices,
        "price_history": price_history,
        "news": news,
    }
