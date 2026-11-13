"""Легковесное ядро крипто-монитора: парсер RSS/API, JSON-кэш, фильтрация и экспорт в PDF."""

from src.cache_manager import CACHE_FILENAME, load_cache, save_cache
from src.core import collect_and_filter_data, export_cached_report_to_pdf, generate_report
from src.parser import clean_html_text, fetch_all_data, fetch_crypto_prices, fetch_rss_news
from src.pdf_exporter import export_report_to_pdf, get_desktop_directory, resolve_resource_path
from src.processor import deduplicate_news, filter_by_coins, filter_by_timeframe, filter_news

__all__ = [
    "CACHE_FILENAME",
    "clean_html_text",
    "collect_and_filter_data",
    "deduplicate_news",
    "export_cached_report_to_pdf",
    "export_report_to_pdf",
    "fetch_all_data",
    "fetch_crypto_prices",
    "fetch_rss_news",
    "filter_by_coins",
    "filter_by_timeframe",
    "filter_news",
    "generate_report",
    "get_desktop_directory",
    "load_cache",
    "resolve_resource_path",
    "save_cache",
]
