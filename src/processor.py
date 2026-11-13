"""Модуль фильтрации и дедупликации новостей на чистых структурах данных Python (без Pandas)."""

from __future__ import annotations

import re
import time
from typing import Any

# Ключевые слова и паттерны с границами слов для каждой монеты (избегаем ложных срабатываний)
COIN_PATTERNS: dict[str, re.Pattern[str]] = {
    "BTC": re.compile(r"\b(btc|bitcoin|биткоин\w*|satoshi)\b", re.IGNORECASE),
    "ETH": re.compile(r"\b(eth|ethereum|эфириум\w*|эфир\w*|vitalik)\b", re.IGNORECASE),
    "SOL": re.compile(r"\b(sol|solana|солан\w*)\b", re.IGNORECASE),
    "LINK": re.compile(r"\b(link|chainlink|чейнлинк\w*|ccip)\b", re.IGNORECASE),
    "BNB": re.compile(r"\b(bnb|binance\s*coin|bnb\s*chain|binance)\b", re.IGNORECASE),
    "XRP": re.compile(r"\b(xrp|ripple|рипл\w*|rlusd)\b", re.IGNORECASE),
}

# Стоп-слова для отсева рекламного шума и спама (согласно SKILL.md)
SPAM_MARKERS: tuple[str, ...] = (
    "sponsored",
    "press release",
    "partner content",
    "advertorial",
    "airdrop giveaway",
    "promo code",
    "casino",
    "betting",
    "100x gem",
    "presale now",
)

# Перевод строковых значений периода в секунды
TIMEFRAME_SECONDS: dict[str, int] = {
    # Короткие ключи
    "1h": 3600,
    "6h": 6 * 3600,
    "24h": 24 * 3600,
    "3d": 3 * 24 * 3600,
    "7d": 7 * 24 * 3600,
    "30d": 30 * 24 * 3600,
    # Ключи из GUI (Timeline)
    "Timeline: За 1 час": 3600,
    "Timeline: За 6 часов": 6 * 3600,
    "Timeline: За 24 часа": 24 * 3600,
    "Timeline: За 3 дня": 3 * 24 * 3600,
    "Timeline: За неделю": 7 * 24 * 3600,
    "Timeline: За месяц": 30 * 24 * 3600,
    "За 1 час": 3600,
    "За 6 часов": 6 * 3600,
    "За 24 часа": 24 * 3600,
    "За 3 дня": 3 * 24 * 3600,
    "За 7 дней": 7 * 24 * 3600,
    "За неделю": 7 * 24 * 3600,
    "За месяц": 30 * 24 * 3600,
}

RE_NON_ALNUM = re.compile(r"[^\w\s]", re.UNICODE)


def _normalize_title(title: str) -> str:
    """Нормализует заголовок для точного выявления дубликатов."""
    cleaned = RE_NON_ALNUM.sub("", title.lower())
    return " ".join(cleaned.split())


def is_spam_or_noise(item: dict[str, Any]) -> bool:
    """Проверяет запись на наличие рекламных маркеров или слишком короткого заголовка."""
    title = (item.get("title") or "").strip()
    if len(title) < 15:
        return True

    combined = f"{title} {item.get('summary') or ''}".lower()
    for marker in SPAM_MARKERS:
        if marker in combined:
            return True
    return False


def deduplicate_news(news_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Удаляет дубликаты новостей по нормализованному заголовку и ссылке."""
    seen_titles: set[str] = set()
    seen_links: set[str] = set()
    unique_items: list[dict[str, Any]] = []

    for item in news_items:
        if not isinstance(item, dict):
            continue
        raw_title = (item.get("title") or "").strip()
        if not raw_title or is_spam_or_noise(item):
            continue

        norm_title = _normalize_title(raw_title)
        link = (item.get("link") or "").strip()

        if norm_title in seen_titles:
            continue
        if link and link in seen_links:
            continue

        seen_titles.add(norm_title)
        if link:
            seen_links.add(link)
        unique_items.append(item)

    return unique_items


def resolve_timeframe_seconds(timeframe: str) -> int:
    """Преобразует строковый идентификатор периода в количество секунд (по умолчанию 24ч)."""
    tf = (timeframe or "").strip()
    if tf in TIMEFRAME_SECONDS:
        return TIMEFRAME_SECONDS[tf]

    tf_lower = tf.lower()
    if "1 час" in tf_lower or tf_lower == "1h":
        return 3600
    if "6 час" in tf_lower or tf_lower == "6h":
        return 6 * 3600
    if "3 дн" in tf_lower or tf_lower == "3d":
        return 3 * 24 * 3600
    if "недел" in tf_lower or "7 дн" in tf_lower or tf_lower == "7d":
        return 7 * 24 * 3600
    if "месяц" in tf_lower or "30 дн" in tf_lower or tf_lower == "30d":
        return 30 * 24 * 3600
    return 24 * 3600


def filter_by_timeframe(
    news_items: list[dict[str, Any]],
    timeframe: str = "24h",
    now_ts: float | None = None,
) -> list[dict[str, Any]]:
    """Фильтрует список новостей по времени публикации (24ч, 3 дня, 7 дней, месяц и т.д.)."""
    current_ts = now_ts if now_ts is not None else time.time()
    max_age_seconds = resolve_timeframe_seconds(timeframe)
    cutoff_ts = current_ts - max_age_seconds

    filtered: list[dict[str, Any]] = []
    for item in news_items:
        pub_ts = float(item.get("published_ts") or 0.0)
        if pub_ts <= 0.0 or pub_ts >= cutoff_ts:
            filtered.append(item)

    # Сортируем от самых свежих к более старым
    filtered.sort(key=lambda x: float(x.get("published_ts") or 0.0), reverse=True)
    return filtered


def filter_by_coins(
    news_items: list[dict[str, Any]],
    selected_coins: list[str],
) -> list[dict[str, Any]]:
    """Фильтрует новости по упоминанию выбранных монет (тикеров и названий)."""
    normalized_coins = [c.strip().upper() for c in selected_coins if c.strip()]
    if not normalized_coins:
        return []

    matched_news: list[dict[str, Any]] = []
    for item in news_items:
        searchable_text = f"{item.get('title', '')} {item.get('summary', '')}"
        matched_tickers: list[str] = []

        for ticker in normalized_coins:
            pattern = COIN_PATTERNS.get(ticker)
            if pattern is not None:
                if pattern.search(searchable_text):
                    matched_tickers.append(ticker)
            else:
                # Резервный поиск по точному слову для пользовательских тикеров
                fallback_re = re.compile(rf"\b{re.escape(ticker)}\b", re.IGNORECASE)
                if fallback_re.search(searchable_text):
                    matched_tickers.append(ticker)

        if matched_tickers:
            enriched_item = dict(item)
            enriched_item["matched_coins"] = matched_tickers
            matched_news.append(enriched_item)

    return matched_news


def filter_news(
    news_items: list[dict[str, Any]],
    selected_coins: list[str],
    timeframe: str = "24h",
) -> list[dict[str, Any]]:
    """Полный пайплайн фильтрации на стандартных списках/словарях: дедупликация -> период -> монеты."""
    unique_items = deduplicate_news(news_items)
    time_filtered = filter_by_timeframe(unique_items, timeframe=timeframe)
    coin_filtered = filter_by_coins(time_filtered, selected_coins=selected_coins)
    return coin_filtered
