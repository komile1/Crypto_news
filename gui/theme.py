"""Дизайн-система, цветовая палитра и типографика интерфейса (CustomTkinter)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemePalette:
    """Цветовые токены в стиле Deep Cyber Navy по референсу."""

    # Фоновые поверхности
    bg_root: str = "#070E17"          # Глубокий темно-синий фон окна
    bg_rail: str = "#050B12"          # Узкая левая панель иконок
    bg_sidebar: str = "#091320"       # Левая панель управления «Крипто Монитор»
    bg_topbar: str = "#0A1523"        # Верхняя информационная панель справа
    bg_card_outer: str = "#0B1624"    # Внешний контейнер карточки новостей
    bg_card_inner: str = "#07101C"    # Внутреннее поле превью новостей
    bg_input: str = "#0B1624"         # Фон выпадающего списка и прогресс-бара

    # Состояния строк фильтра (чекбоксов)
    bg_row_idle: str = "transparent"
    bg_row_selected: str = "#0F2742"  # Подсветка активной строки как на референсе
    bg_row_hover: str = "#0B1E35"

    # Границы и разделители
    border_subtle: str = "#15263B"
    border_card: str = "#1B324E"
    border_input: str = "#1E3552"
    border_inner: str = "#14273E"

    # Акцентные цвета
    accent_cyan: str = "#45F0FF"        # Неоново-голубая кнопка «Сгенерировать рапорт»
    accent_cyan_hover: str = "#75F5FF"
    accent_checkbox: str = "#2CE5FF"    # Голубой цвет активного чекбокса
    accent_blue: str = "#0E64DF"        # Синяя кнопка «Скачать PDF»
    accent_blue_hover: str = "#1E78F8"

    # Текст
    text_primary: str = "#ECF4FF"
    text_secondary: str = "#9AB0CA"
    text_muted: str = "#56708F"
    text_on_cyan: str = "#04121E"

    # Индикаторы статуса
    status_online: str = "#38E8FF"
    status_dot_mid: str = "#5CE1E6"
    status_dot_low: str = "#D4E8FF"


PALETTE = ThemePalette()

# Набор поддерживаемых криптовалют для фильтрации
DEFAULT_COINS: list[tuple[str, str, bool]] = [
    ("BTC", "BTC  •  Bitcoin", True),
    ("ETH", "ETH  •  Ethereum", False),
    ("SOL", "SOL  •  Solana", True),
    ("BNB", "BNB  •  Binance Coin", False),
    ("XRP", "XRP  •  Ripple", False),
    ("LINK", "LINK  •  Chainlink", False),
]

# Периоды мониторинга (Timeline)
TIMELINE_OPTIONS: list[str] = [
    "Timeline: За 24 часа",
    "Timeline: За 6 часов",
    "Timeline: За 1 час",
    "Timeline: За неделю",
    "Timeline: За месяц",
]
