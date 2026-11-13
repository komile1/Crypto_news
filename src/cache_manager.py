"""Модуль управления легковесным временным JSON-кэшем (temp_data.json)."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

CACHE_FILENAME: str = "temp_data.json"


def get_cache_path(filename: str = CACHE_FILENAME) -> str:
    """Возвращает путь к файлу кэша в рабочей директории пользователя (совместимо с PyInstaller)."""
    return os.path.abspath(os.path.join(os.getcwd(), filename))


def save_cache(data: dict[str, Any], filename: str = CACHE_FILENAME) -> str:
    """Полностью перезаписывает файл temp_data.json новыми собранными данными."""
    cache_path = get_cache_path(filename)
    try:
        with open(cache_path, mode="w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        return cache_path
    except Exception as exc:
        print(
            f"[PARSER ERROR] Cache Write ({cache_path}): {type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        return cache_path


def load_cache(filename: str = CACHE_FILENAME) -> dict[str, Any]:
    """Читает данные из временного файла кэша temp_data.json."""
    cache_path = get_cache_path(filename)
    if not os.path.exists(cache_path):
        return {"updated_at": "", "timestamp": 0.0, "prices": {}, "news": []}

    try:
        with open(cache_path, mode="r", encoding="utf-8") as file:
            data = json.load(file)
            if isinstance(data, dict):
                return data
    except Exception as exc:
        print(
            f"[PARSER ERROR] Cache Read ({cache_path}): {type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
    return {"updated_at": "", "timestamp": 0.0, "prices": {}, "news": []}
