"""Центральная точка входа бизнес-логики: парсинг -> JSON-кэш -> фильтрация -> экспорт в PDF."""

from __future__ import annotations

from typing import Any

from src.cache_manager import load_cache, save_cache
from src.parser import fetch_all_data
from src.pdf_exporter import export_report_to_pdf
from src.processor import filter_news


def collect_and_filter_data(selected_coins: list[str], timeframe: str) -> dict[str, Any]:
    """
    Выполняет сбор данных из RSS/API, перезаписывает temp_data.json
    и фильтрует новости по выбранным монетам и периоду.
    """
    normalized_coins = [str(c).strip().upper() for c in selected_coins if str(c).strip()]

    # Шаг 1: Сбор свежих данных из RSS и CoinGecko API
    raw_data = fetch_all_data(selected_coins=normalized_coins)

    # Шаг 2: Полная перезапись временного кэша temp_data.json
    cache_path = save_cache(raw_data)

    # Шаг 3: Легковесная фильтрация на стандартных списках и словарях Python
    filtered_news = filter_news(
        news_items=raw_data.get("news", []),
        selected_coins=normalized_coins,
        timeframe=timeframe,
    )

    return {
        "updated_at": raw_data.get("updated_at", ""),
        "cache_path": cache_path,
        "prices": raw_data.get("prices", {}),
        "news": filtered_news,
        "total_raw_news": len(raw_data.get("news", [])),
    }


def generate_report(
    selected_coins: list[str],
    timeframe: str,
    export_pdf: bool = True,
) -> dict[str, Any]:
    """
    Объединяет все шаги бэкенда:
    1. Вызывает парсер RSS-лент и котировок CoinGecko.
    2. Полностью перезаписывает временный кэш temp_data.json.
    3. Фильтрует новости по дубликатам, периоду и выбранным монетам (без Pandas).
    4. Генерирует PDF-рапорт на Рабочем столе пользователя (если export_pdf=True).
    """
    normalized_coins = [str(c).strip().upper() for c in selected_coins if str(c).strip()]
    result = collect_and_filter_data(selected_coins=normalized_coins, timeframe=timeframe)

    pdf_path = ""
    if export_pdf:
        pdf_path = export_report_to_pdf(
            prices=result.get("prices", {}),
            news_items=result.get("news", []),
            selected_coins=normalized_coins,
            timeframe=timeframe,
        )

    result["pdf_path"] = pdf_path
    return result


def export_cached_report_to_pdf(selected_coins: list[str], timeframe: str) -> str:
    """Генерирует PDF на Рабочем столе из актуального кэша temp_data.json (или собирает данные, если кэш пуст)."""
    normalized_coins = [str(c).strip().upper() for c in selected_coins if str(c).strip()]
    cached = load_cache()
    if not cached.get("news") and not cached.get("prices"):
        report_data = generate_report(normalized_coins, timeframe, export_pdf=True)
        return str(report_data.get("pdf_path", ""))

    filtered_news = filter_news(
        news_items=cached.get("news", []),
        selected_coins=normalized_coins,
        timeframe=timeframe,
    )
    return export_report_to_pdf(
        prices=cached.get("prices", {}),
        news_items=filtered_news,
        selected_coins=normalized_coins,
        timeframe=timeframe,
    )
