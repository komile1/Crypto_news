---
name: crypto-parser
description: >-
  Instructions and patterns for safe HTML tag sanitization from crypto RSS feeds,
  entity decoding, noise/spam filtering, and ticker-based news categorization.
  Use this skill when implementing or updating RSS and API parsers in src/.
---

# Crypto Parser Skill: Очистка RSS-лент и фильтрация инфошума

Этот скилл определяет стандарты безопасного извлечения, очистки и фильтрации криптовалютных новостей из RSS-лент (`feedparser`) и открытых API перед сохранением во временный JSON-кэш и `pandas.DataFrame`.

---

## 1. Безопасная очистка HTML-тегов и сущностей (HTML Sanitization)

RSS-ленты часто содержат сырой HTML в полях `summary`, `description` и `title` (включая `<script>`, `<style>`, `<iframe>`, `<img>`, рекламные пиксели и битую разметку).

### Правила очистки:
1. **Удаление опасных блоков целиком вместе с содержимым:** Сначала удалять парные теги `<script>...</script>` и `<style>...</style>` регулярным выражением с флагом `re.DOTALL | re.IGNORECASE`.
2. **Замена блочных тегов на пробелы/переносы:** Теги `<br>`, `<p>`, `</div>`, `</li>` заменять на пробел или перенос строки, чтобы слова не склеивались при удалении тегов.
3. **Удаление всех остальных тегов:** Использовать `re.sub(r"<[^>]+>", "", text)`.
4. **Декодирование HTML-сущностей:** Обязательно применять `html.unescape(text)` для преобразования `&amp;`, `&quot;`, `&#8217;`, `&nbsp;` в читаемые символы.
5. **Нормализация пробелов:** Схлопывать множественные пробелы и неразрывные отступы: `re.sub(r"\s+", " ", text).strip()`.

### Эталонный паттерн очистки:
```python
import html
import re

RE_SCRIPTS_STYLES = re.compile(r"<(script|style|iframe|object|embed)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
RE_BLOCK_TAGS = re.compile(r"</?(br|p|div|li|tr|h[1-6])[^>]*>", re.IGNORECASE)
RE_ALL_TAGS = re.compile(r"<[^>]+>")
RE_WHITESPACE = re.compile(r"\s+")


def sanitize_rss_text(raw_html: str | None, max_length: int = 500) -> str:
    """Безопасно очищает HTML из RSS-поля, декодирует сущности и нормализует пробелы."""
    if not raw_html:
        return ""
    text = RE_SCRIPTS_STYLES.sub(" ", raw_html)
    text = RE_BLOCK_TAGS.sub(" ", text)
    text = RE_ALL_TAGS.sub("", text)
    text = html.unescape(text)
    text = RE_WHITESPACE.sub(" ", text).strip()
    if max_length and len(text) > max_length:
        return text[: max_length - 3].rstrip() + "..."
    return text
```

---

## 2. Фильтрация инфошума и спама (Noise & Spam Filtering)

Криптовалютные ленты перегружены рекламными материалами, кликбейтом и нерелевантными прогнозами.

### Правила фильтрации:
1. **Стоп-маркеры (Stop-words / Promoted Content):** Отбрасывать записи, содержащие в заголовке или описании маркеры рекламы и спама (без учета регистра):
   - `sponsored`, `press release`, `partner content`, `advertorial`, `airdrop giveaway`, `promo code`, `casino`, `betting`, `100x gem`, `presale now`.
2. **Минимальная информативность:** Отбрасывать новости с заголовком короче 15 символов или пустым текстом после очистки HTML.
3. **Дедупликация:** При сборе из нескольких RSS-источников удалять дубликаты в `pandas.DataFrame` по нормализованному заголовку (lowercase, без знаков препинания) и `link`.
4. **Фильтрация по тикерам монет:** Сопоставлять новости с выбранными пользователем монетами по словарю синонимов с границами слов (`\b`), чтобы избежать ложных срабатываний (например, `ETH` не должен срабатывать внутри слова `method`):
   - `BTC`: `\b(btc|bitcoin|биткоин\w*)\b`
   - `ETH`: `\b(eth|ethereum|эфириум\w*|эфир\w*)\b`
   - `SOL`: `\b(sol|solana|солан\w*)\b`
   - `BNB`: `\b(bnb|binance coin)\b`
   - `XRP`: `\b(xrp|ripple|рипл\w*)\b`
   - `LINK`: `\b(link|chainlink|чейнлинк\w*)\b`

---

## 3. Обработка ошибок парсинга (Console Error Reporting)

Согласно `AGENTS.md`, любой сбой при получении или парсинге RSS/API обязан логироваться в консоль:

```python
import sys
import traceback

def log_parse_error(source: str, exc: Exception) -> None:
    """Обязательный вывод ошибок парсинга в консоль."""
    print(f"[PARSER ERROR] Источник: {source} | Ошибка: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
```
