"""Главное окно приложения Crypto Monitor & Report на базе CustomTkinter."""

from __future__ import annotations

import os
import sys
import threading
from datetime import datetime
from typing import Any, Callable

import customtkinter as ctk

from gui.theme import DEFAULT_COINS, PALETTE, TIMELINE_OPTIONS
from src.core import collect_and_filter_data
from src.pdf_exporter import export_report_to_pdf, resolve_resource_path


class CryptoMonitorApp(ctk.CTk):
    """Десктопный интерфейс мониторинга криптовалют и генерации PDF-отчетов."""

    def __init__(
        self,
        on_generate_report: Callable[[list[str], str], None] | None = None,
        on_export_pdf: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()

        self._on_generate_report = on_generate_report
        self._on_export_pdf = on_export_pdf
        self._is_busy: bool = False

        # Текущие загруженные данные для мгновенного экспорта в PDF
        self._current_prices: dict[str, dict[str, float]] = {}
        self._current_news: list[dict[str, Any]] = []

        # Глобальная конфигурация темы
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Параметры окна
        self.title("Crypto Monitor & Report")
        self.geometry("1080x660")
        self.minsize(920, 580)
        self.configure(fg_color=PALETTE.bg_root)
        self._apply_window_icon()

        # Состояние фильтров
        self.coin_vars: dict[str, ctk.BooleanVar] = {}
        self.coin_rows: dict[str, ctk.CTkFrame] = {}
        self.timeline_var = ctk.StringVar(value=TIMELINE_OPTIONS[0])

        # Шрифты (Segoe UI на Windows для максимальной четкости кириллицы)
        self.font_title = ctk.CTkFont(family="Segoe UI", size=22, weight="bold")
        self.font_section = ctk.CTkFont(family="Segoe UI", size=14, weight="normal")
        self.font_item = ctk.CTkFont(family="Segoe UI", size=14, weight="normal")
        self.font_btn_cyan = ctk.CTkFont(family="Segoe UI", size=15, weight="bold")
        self.font_btn_blue = ctk.CTkFont(family="Segoe UI", size=15, weight="bold")
        self.font_card_header = ctk.CTkFont(family="Segoe UI", size=20, weight="bold")
        self.font_news_title = ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        self.font_news_body = ctk.CTkFont(family="Segoe UI", size=13, weight="normal")
        self.font_meta = ctk.CTkFont(family="Segoe UI", size=11, weight="normal")

        self._setup_layout()
        self._populate_initial_preview()

    def _apply_window_icon(self) -> None:
        """Устанавливает фирменную иконку окна (.ico) с поддержкой PyInstaller."""
        icon_path = resolve_resource_path(os.path.join("assets", "app_icon.ico"))
        if os.path.isfile(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception as exc:
                print(
                    f"[PARSER ERROR] Window Icon ({icon_path}): {type(exc).__name__}: {exc}",
                    file=sys.stderr,
                    flush=True,
                )

    # ------------------------------------------------------------------
    # Построение интерфейса
    # ------------------------------------------------------------------

    def _setup_layout(self) -> None:
        """Создает трехколоночную структуру: Rail (слева), Sidebar (фильтры), Content (превью)."""
        self.grid_columnconfigure(0, weight=0, minsize=54)   # Узкая панель иконок
        self.grid_columnconfigure(1, weight=0, minsize=295)  # Панель «Крипто Монитор»
        self.grid_columnconfigure(2, weight=1)               # Правая область контента
        self.grid_rowconfigure(0, weight=1)

        self._build_icon_rail()
        self._build_sidebar()
        self._build_main_content()

    def _build_icon_rail(self) -> None:
        """Создает левую вертикальную панель навигации с неоновым индикатором."""
        self.rail_frame = ctk.CTkFrame(
            self,
            width=54,
            corner_radius=0,
            fg_color=PALETTE.bg_rail,
            border_width=1,
            border_color=PALETTE.border_subtle,
        )
        self.rail_frame.grid(row=0, column=0, sticky="nsew")
        self.rail_frame.grid_propagate(False)
        self.rail_frame.grid_columnconfigure(0, weight=1)
        self.rail_frame.grid_rowconfigure(4, weight=1)  # Распорка по центру

        # Активная вкладка «Рапорт» с голубым вертикальным индикатором слева
        active_item_holder = ctk.CTkFrame(self.rail_frame, fg_color="transparent", height=48)
        active_item_holder.grid(row=0, column=0, sticky="ew", pady=(16, 4))
        active_item_holder.grid_columnconfigure(1, weight=1)

        indicator = ctk.CTkFrame(
            active_item_holder,
            width=4,
            height=34,
            corner_radius=2,
            fg_color=PALETTE.accent_cyan,
        )
        indicator.grid(row=0, column=0, padx=(2, 0), pady=6)

        self.btn_nav_report = ctk.CTkButton(
            active_item_holder,
            text="📄",
            width=38,
            height=38,
            corner_radius=8,
            fg_color="#0D2238",
            hover_color="#143252",
            text_color=PALETTE.accent_cyan,
            font=ctk.CTkFont(size=18),
            command=self._focus_report_view,
        )
        self.btn_nav_report.grid(row=0, column=1, padx=(4, 8))

        # Кнопка открытия рабочей папки (Кэш / PDF)
        self.btn_nav_folder = ctk.CTkButton(
            self.rail_frame,
            text="📁",
            width=38,
            height=38,
            corner_radius=8,
            fg_color="transparent",
            hover_color="#0E1E32",
            text_color=PALETTE.text_secondary,
            font=ctk.CTkFont(size=17),
            command=self._open_working_directory,
        )
        self.btn_nav_folder.grid(row=1, column=0, pady=6)

        # Кнопка «О программе / Справка»
        self.btn_nav_info = ctk.CTkButton(
            self.rail_frame,
            text="ⓘ",
            width=38,
            height=38,
            corner_radius=8,
            fg_color="transparent",
            hover_color="#0E1E32",
            text_color=PALETTE.text_secondary,
            font=ctk.CTkFont(size=18),
            command=self._show_system_info_in_preview,
        )
        self.btn_nav_info.grid(row=2, column=0, pady=6)

        # Нижний блок индикаторов и шестеренки (как на референсе)
        bottom_rail = ctk.CTkFrame(self.rail_frame, fg_color="transparent")
        bottom_rail.grid(row=5, column=0, pady=(0, 14))

        for idx, dot_color in enumerate(
            (PALETTE.text_muted, PALETTE.status_dot_mid, PALETTE.status_dot_low)
        ):
            dot = ctk.CTkLabel(
                bottom_rail,
                text="●",
                text_color=dot_color,
                font=ctk.CTkFont(size=12),
                height=18,
            )
            dot.grid(row=idx, column=0, pady=3)

        self.btn_nav_settings = ctk.CTkButton(
            bottom_rail,
            text="⚙",
            width=36,
            height=36,
            corner_radius=8,
            fg_color="transparent",
            hover_color="#0E1E32",
            text_color=PALETTE.text_secondary,
            font=ctk.CTkFont(size=18),
            command=self._show_system_info_in_preview,
        )
        self.btn_nav_settings.grid(row=3, column=0, pady=(10, 0))

    def _build_sidebar(self) -> None:
        """Создает левую панель управления «Крипто Монитор» с фильтрами, кнопкой, периодом и прогрессом."""
        self.sidebar_frame = ctk.CTkFrame(
            self,
            width=295,
            corner_radius=0,
            fg_color=PALETTE.bg_sidebar,
        )
        self.sidebar_frame.grid(row=0, column=1, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)
        self.sidebar_frame.grid_columnconfigure(0, weight=1)

        # Заголовок «Крипто Монитор»
        self.lbl_app_title = ctk.CTkLabel(
            self.sidebar_frame,
            text="Крипто Монитор",
            font=self.font_title,
            text_color=PALETTE.text_primary,
            anchor="w",
        )
        self.lbl_app_title.grid(row=0, column=0, sticky="ew", padx=22, pady=(22, 12))

        # Тонкая горизонтальная линия под заголовком
        divider = ctk.CTkFrame(
            self.sidebar_frame,
            height=1,
            fg_color=PALETTE.border_subtle,
        )
        divider.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 16))

        # Заголовок секции Filter + быстрые кнопки выбора
        filter_header = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        filter_header.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 8))
        filter_header.grid_columnconfigure(0, weight=1)

        lbl_filter = ctk.CTkLabel(
            filter_header,
            text="Filter",
            font=self.font_section,
            text_color=PALETTE.text_secondary,
            anchor="w",
        )
        lbl_filter.grid(row=0, column=0, sticky="w")

        btn_select_all = ctk.CTkButton(
            filter_header,
            text="Все",
            width=36,
            height=22,
            corner_radius=4,
            fg_color="#0F2136",
            hover_color="#173252",
            text_color=PALETTE.text_secondary,
            font=self.font_meta,
            command=self._select_all_coins,
        )
        btn_select_all.grid(row=0, column=1, padx=(0, 4))

        btn_reset_all = ctk.CTkButton(
            filter_header,
            text="Сброс",
            width=46,
            height=22,
            corner_radius=4,
            fg_color="#0F2136",
            hover_color="#173252",
            text_color=PALETTE.text_secondary,
            font=self.font_meta,
            command=self._clear_all_coins,
        )
        btn_reset_all.grid(row=0, column=2)

        # Список чекбоксов с подсветкой выбранных строк (как на референсе)
        self.filter_list_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.filter_list_frame.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 18))
        self.filter_list_frame.grid_columnconfigure(0, weight=1)

        for idx, (ticker, label_text, default_checked) in enumerate(DEFAULT_COINS):
            var = ctk.BooleanVar(value=default_checked)
            self.coin_vars[ticker] = var

            row_frame = ctk.CTkFrame(
                self.filter_list_frame,
                height=36,
                corner_radius=6,
                fg_color=PALETTE.bg_row_selected if default_checked else PALETTE.bg_row_idle,
            )
            row_frame.grid(row=idx, column=0, sticky="ew", pady=2)
            row_frame.grid_columnconfigure(0, weight=1)
            self.coin_rows[ticker] = row_frame

            cb = ctk.CTkCheckBox(
                row_frame,
                text=label_text,
                variable=var,
                font=self.font_item,
                text_color=PALETTE.text_primary,
                fg_color=PALETTE.accent_checkbox,
                hover_color=PALETTE.accent_cyan_hover,
                checkmark_color=PALETTE.text_on_cyan,
                border_color="#2D4A6D",
                border_width=2,
                checkbox_width=20,
                checkbox_height=20,
                corner_radius=5,
                command=lambda t=ticker: self._on_coin_toggled(t),
            )
            cb.grid(row=0, column=0, sticky="w", padx=10, pady=6)

        # Яркая голубая кнопка «Сгенерировать рапорт»
        self.btn_generate = ctk.CTkButton(
            self.sidebar_frame,
            text="Сгенерировать рапорт",
            height=44,
            corner_radius=8,
            fg_color=PALETTE.accent_cyan,
            hover_color=PALETTE.accent_cyan_hover,
            text_color=PALETTE.text_on_cyan,
            font=self.font_btn_cyan,
            command=self._handle_generate_clicked,
        )
        self.btn_generate.grid(row=4, column=0, sticky="ew", padx=22, pady=(0, 16))

        # Выпадающий список периода (Timeline) в рамке
        timeline_holder = ctk.CTkFrame(
            self.sidebar_frame,
            fg_color=PALETTE.bg_input,
            border_width=1,
            border_color=PALETTE.border_input,
            corner_radius=7,
        )
        timeline_holder.grid(row=5, column=0, sticky="ew", padx=22, pady=(0, 20))
        timeline_holder.grid_columnconfigure(0, weight=1)

        self.option_timeline = ctk.CTkOptionMenu(
            timeline_holder,
            variable=self.timeline_var,
            values=TIMELINE_OPTIONS,
            height=36,
            corner_radius=6,
            fg_color=PALETTE.bg_input,
            button_color="#102033",
            button_hover_color="#19314D",
            dropdown_fg_color="#0B1726",
            dropdown_hover_color="#162D49",
            dropdown_text_color=PALETTE.text_primary,
            text_color=PALETTE.text_primary,
            font=self.font_item,
            command=self._on_timeline_changed,
        )
        self.option_timeline.grid(row=0, column=0, sticky="ew", padx=2, pady=2)

        # Секция Progress
        progress_header = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        progress_header.grid(row=6, column=0, sticky="ew", padx=22, pady=(0, 6))
        progress_header.grid_columnconfigure(0, weight=1)

        lbl_progress = ctk.CTkLabel(
            progress_header,
            text="Progress",
            font=self.font_section,
            text_color=PALETTE.text_secondary,
            anchor="w",
        )
        lbl_progress.grid(row=0, column=0, sticky="w")

        self.lbl_progress_status = ctk.CTkLabel(
            progress_header,
            text="Готов к сбору",
            font=self.font_meta,
            text_color=PALETTE.text_muted,
            anchor="e",
        )
        self.lbl_progress_status.grid(row=0, column=1, sticky="e")

        self.progress_bar = ctk.CTkProgressBar(
            self.sidebar_frame,
            height=14,
            corner_radius=7,
            fg_color=PALETTE.bg_input,
            progress_color=PALETTE.accent_cyan,
            border_width=1,
            border_color=PALETTE.border_input,
        )
        self.progress_bar.grid(row=7, column=0, sticky="ew", padx=22, pady=(0, 12))
        self.progress_bar.set(0.36)

    def _build_main_content(self) -> None:
        """Создает правую область: верхнюю строку котировок, карточку «Топ-5 новостей» и кнопку «Скачать PDF»."""
        self.right_container = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=PALETTE.bg_root,
        )
        self.right_container.grid(row=0, column=2, sticky="nsew", padx=(8, 22), pady=20)
        self.right_container.grid_columnconfigure(0, weight=1)
        self.right_container.grid_rowconfigure(1, weight=1)

        # 1. Верхняя информационная плашка (котировки и статус кэша)
        self.top_bar = ctk.CTkFrame(
            self.right_container,
            height=46,
            corner_radius=8,
            fg_color=PALETTE.bg_topbar,
            border_width=1,
            border_color=PALETTE.border_subtle,
        )
        self.top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        self.top_bar.grid_propagate(False)
        self.top_bar.grid_columnconfigure(0, weight=1)

        self.lbl_market_bar = ctk.CTkLabel(
            self.top_bar,
            text="⚡ Нажмите «Сгенерировать рапорт» для загрузки актуальных котировок и RSS",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=PALETTE.text_secondary,
            anchor="w",
        )
        self.lbl_market_bar.grid(row=0, column=0, sticky="w", padx=16, pady=10)

        self.lbl_cache_badge = ctk.CTkLabel(
            self.top_bar,
            text="JSON Cache: Ready",
            font=self.font_meta,
            text_color=PALETTE.accent_cyan,
            anchor="e",
        )
        self.lbl_cache_badge.grid(row=0, column=1, sticky="e", padx=16, pady=10)

        # 2. Внешний контейнер карточки новостей + кнопки PDF
        self.card_outer = ctk.CTkFrame(
            self.right_container,
            corner_radius=10,
            fg_color=PALETTE.bg_card_outer,
            border_width=1,
            border_color=PALETTE.border_card,
        )
        self.card_outer.grid(row=1, column=0, sticky="nsew")
        self.card_outer.grid_columnconfigure(0, weight=1)
        self.card_outer.grid_rowconfigure(0, weight=1)

        # Внутренняя рамка карточки с заголовком «Топ-5 новостей» и текстовым превью
        self.card_inner = ctk.CTkFrame(
            self.card_outer,
            corner_radius=8,
            fg_color=PALETTE.bg_card_inner,
            border_width=1,
            border_color=PALETTE.border_inner,
        )
        self.card_inner.grid(row=0, column=0, sticky="nsew", padx=14, pady=(14, 12))
        self.card_inner.grid_columnconfigure(0, weight=1)
        self.card_inner.grid_rowconfigure(1, weight=1)

        # Шапка внутри окна превью
        preview_header_frame = ctk.CTkFrame(self.card_inner, fg_color="transparent")
        preview_header_frame.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 4))
        preview_header_frame.grid_columnconfigure(0, weight=1)

        self.lbl_preview_title = ctk.CTkLabel(
            preview_header_frame,
            text="Топ-5 новостей",
            font=self.font_card_header,
            text_color=PALETTE.text_primary,
            anchor="w",
        )
        self.lbl_preview_title.grid(row=0, column=0, sticky="w")

        self.lbl_active_filters = ctk.CTkLabel(
            preview_header_frame,
            text="Активные монеты: BTC, SOL  |  За 24 часа",
            font=self.font_meta,
            text_color=PALETTE.text_muted,
            anchor="e",
        )
        self.lbl_active_filters.grid(row=0, column=1, sticky="e")

        # Текстовое окно превью (CTkTextbox согласно AGENTS.md)
        self.preview_textbox = ctk.CTkTextbox(
            self.card_inner,
            fg_color=PALETTE.bg_card_inner,
            text_color=PALETTE.text_primary,
            font=self.font_news_body,
            border_width=0,
            corner_radius=6,
            wrap="word",
            scrollbar_button_color="#172C46",
            scrollbar_button_hover_color="#25466E",
            activate_scrollbars=True,
        )
        self.preview_textbox.grid(row=1, column=0, sticky="nsew", padx=12, pady=(2, 12))

        # Настройка цветовых тегов внутри текстового поля для красивой типографики
        tb = self.preview_textbox._textbox
        tb.tag_configure("headline", foreground="#ECF4FF", font=("Segoe UI", 12, "bold"), spacing1=8, spacing3=2)
        tb.tag_configure("summary", foreground="#9FB5D0", font=("Segoe UI", 11), spacing3=4)
        tb.tag_configure("meta", foreground="#4E6B8C", font=("Segoe UI", 9), spacing3=8)
        tb.tag_configure("accent", foreground="#45F0FF", font=("Segoe UI", 11, "bold"))

        # 3. Синяя кнопка «Скачать PDF» во всю ширину нижней части карточки
        self.btn_export_pdf = ctk.CTkButton(
            self.card_outer,
            text="📄  Скачать PDF",
            height=46,
            corner_radius=8,
            fg_color=PALETTE.accent_blue,
            hover_color=PALETTE.accent_blue_hover,
            text_color="#FFFFFF",
            font=self.font_btn_blue,
            command=self._handle_export_pdf_clicked,
        )
        self.btn_export_pdf.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 14))

    # ------------------------------------------------------------------
    # Обработчики событий и методы обновления UI
    # ------------------------------------------------------------------

    def get_selected_coins(self) -> list[str]:
        """Возвращает список выбранных тикеров криптовалют."""
        return [ticker for ticker, var in self.coin_vars.items() if var.get()]

    def get_selected_timeline(self) -> str:
        """Возвращает выбранный период мониторинга."""
        return self.timeline_var.get()

    def _on_coin_toggled(self, ticker: str) -> None:
        """Обновляет подсветку строки чекбокса и бейдж активных фильтров."""
        is_checked = self.coin_vars[ticker].get()
        row = self.coin_rows.get(ticker)
        if row is not None:
            row.configure(
                fg_color=PALETTE.bg_row_selected if is_checked else PALETTE.bg_row_idle
            )
        self._update_filter_badge()

    def _on_timeline_changed(self, _value: str) -> None:
        """Обновляет бейдж периода при смене значения в выпадающем списке."""
        self._update_filter_badge()

    def _select_all_coins(self) -> None:
        """Отмечает все чекбоксы монет."""
        for ticker, var in self.coin_vars.items():
            var.set(True)
            self.coin_rows[ticker].configure(fg_color=PALETTE.bg_row_selected)
        self._update_filter_badge()

    def _clear_all_coins(self) -> None:
        """Снимает выделение со всех чекбоксов монет."""
        for ticker, var in self.coin_vars.items():
            var.set(False)
            self.coin_rows[ticker].configure(fg_color=PALETTE.bg_row_idle)
        self._update_filter_badge()

    def _update_filter_badge(self) -> None:
        """Синхронизирует подпись выбранных монет и периода в шапке превью."""
        coins = self.get_selected_coins()
        coins_str = ", ".join(coins) if coins else "Не выбраны"
        period_short = self.get_selected_timeline().replace("Timeline: ", "")
        self.lbl_active_filters.configure(
            text=f"Активные монеты: {coins_str}  |  {period_short}"
        )

    def _populate_initial_preview(self) -> None:
        """Заполняет окно превью стартовыми новостями до первого нажатия «Сгенерировать рапорт»."""
        sample_items = [
            (
                "1. [BTC] Институциональный приток в спотовые Bitcoin-ETF обновил недельный максимум",
                "Крупнейшие фонды зафиксировали чистый приток капитала на фоне стабилизации макроэкономических показателей и роста ликвидности.",
                "Источник: CoinDesk RSS  •  Готов к живому обновлению  •  Тикер: BTC",
            ),
            (
                "2. [SOL] Экосистема Solana обработала рекордный объем транзакций в DEX-протоколах",
                "Суточный объем торгов в децентрализованных пулах ликвидности вырос на 18%, комиссионные издержки остаются ниже $0.01.",
                "Источник: Cointelegraph RSS  •  Готов к живому обновлению  •  Тикер: SOL",
            ),
            (
                "3. [ETH] Разработчики Ethereum согласовали график оптимизации валидаторов в следующем обновлении",
                "Обновление направлено на снижение нагрузки на ноды и ускорение финализации блоков в периоды пиковой активности сети.",
                "Источник: Decrypt RSS  •  Готов к живому обновлению  •  Тикер: ETH",
            ),
            (
                "4. [LINK] Протокол кросс-чейн совместимости Chainlink CCIP расширяет интеграцию в DeFi",
                "Децентрализованные оракулы обеспечили верификацию кросс-чейн транзакций для новых пулов ликвидности.",
                "Источник: CoinDesk RSS  •  Готов к живому обновлению  •  Тикер: LINK",
            ),
            (
                "5. [BNB / XRP] Обзор ликвидности крупнейших альткоинов на глобальных спотовых площадках",
                "Торговая активность сохраняет устойчивость, нажмите «Сгенерировать рапорт» слева для получения свежих RSS-лент и цен CoinGecko.",
                "Источник: Cointelegraph RSS  •  Готов к живому обновлению",
            ),
        ]
        self.render_news_items(sample_items)

    def render_news_items(self, items: list[tuple[str, str, str]]) -> None:
        """Отрисовывает список кортежей (заголовок, описание, мета) в CTkTextbox с форматированием."""
        self.preview_textbox.configure(state="normal")
        self.preview_textbox.delete("1.0", "end")
        tb = self.preview_textbox._textbox

        if not items:
            tb.insert(
                "end",
                "По выбранным монетам и периоду новостей в лентах не найдено.\n"
                "Попробуйте увеличить период (например, «За неделю» или «За месяц») или отметить дополнительные монеты.",
                "summary",
            )
        else:
            for headline, summary, meta in items:
                tb.insert("end", f"{headline}\n", "headline")
                tb.insert("end", f"{summary}\n", "summary")
                tb.insert("end", f"{meta}\n", "meta")

        self.preview_textbox.configure(state="disabled")

    def _format_market_bar(self, prices: dict[str, dict[str, float]], selected: list[str]) -> str:
        """Форматирует строку актуальных котировок для верхней панели."""
        if not prices:
            return "⚡ Котировки: нет данных от CoinGecko (проверьте интернет-соединение)"

        order = [c for c in selected if c in prices] or list(prices.keys())
        parts: list[str] = []
        for ticker in order[:4]:
            info = prices.get(ticker, {})
            usd = float(info.get("usd", 0.0))
            chg = float(info.get("change_24h", 0.0))
            sign = "+" if chg >= 0 else ""
            price_fmt = f"${usd:,.2f}" if usd >= 1 else f"${usd:,.4f}"
            parts.append(f"{ticker} {price_fmt} ({sign}{chg:.1f}%)")

        return "⚡ Рынок: " + "   •   ".join(parts)

    def set_progress(self, value: float, status_text: str) -> None:
        """Обновляет индикатор прогресса (0.0 .. 1.0) и текстовый статус."""
        clamped = max(0.0, min(1.0, value))
        self.progress_bar.set(clamped)
        self.lbl_progress_status.configure(text=status_text)

    # ------------------------------------------------------------------
    # Боевая интеграция с src/core.py в фоновом потоке
    # ------------------------------------------------------------------

    def _handle_generate_clicked(self) -> None:
        """Обработчик нажатия кнопки «Сгенерировать рапорт»."""
        if self._is_busy:
            return

        selected = self.get_selected_coins()
        timeline = self.get_selected_timeline()

        if not selected:
            self.set_progress(0.0, "Выберите монеты!")
            self.render_news_items([])
            return

        if self._on_generate_report is not None:
            self._on_generate_report(selected, timeline)
            return

        self._is_busy = True
        self.btn_generate.configure(state="disabled", text="Сбор данных...")
        self.set_progress(0.25, "Запрос RSS и CoinGecko...")

        worker = threading.Thread(
            target=self._run_collect_worker,
            args=(selected, timeline),
            daemon=True,
        )
        worker.start()

    def _run_collect_worker(self, selected: list[str], timeline: str) -> None:
        """Фоновый поток сбора RSS/API, записи temp_data.json и фильтрации."""
        try:
            result = collect_and_filter_data(selected_coins=selected, timeframe=timeline)
            self.after(0, lambda: self._on_collect_finished(selected, result, None))
        except Exception as exc:
            print(
                f"[PARSER ERROR] Worker Thread: {type(exc).__name__}: {exc}",
                file=sys.stderr,
                flush=True,
            )
            self.after(0, lambda e=exc: self._on_collect_finished(selected, None, e))

    def _on_collect_finished(
        self,
        selected: list[str],
        result: dict[str, Any] | None,
        error: Exception | None,
    ) -> None:
        """Обновляет GUI после завершения фонового сбора и фильтрации данных."""
        self._is_busy = False
        self.btn_generate.configure(state="normal", text="Сгенерировать рапорт")

        if error is not None or result is None:
            self.set_progress(0.0, "Ошибка сбора (см. консоль)")
            return

        self._current_prices = result.get("prices", {})
        self._current_news = result.get("news", [])

        # Обновляем верхнюю панель котировок и статус JSON-кэша
        self.lbl_market_bar.configure(text=self._format_market_bar(self._current_prices, selected))
        now_short = datetime.now().strftime("%H:%M:%S")
        self.lbl_cache_badge.configure(text=f"temp_data.json: {now_short}")

        # Отрисовываем отфильтрованные новости
        formatted_items: list[tuple[str, str, str]] = []
        for idx, item in enumerate(self._current_news, start=1):
            matched = ", ".join(item.get("matched_coins") or selected)
            title = f"{idx}. [{matched}] {item.get('title', 'Без заголовка')}"
            summary = item.get("summary") or "Описание отсутствует."
            source = item.get("source") or "RSS"
            pub_str = item.get("published_str") or ""
            meta = f"Источник: {source}   •   {pub_str}   •   Тикеры: {matched}"
            formatted_items.append((title, summary, meta))

        count = len(formatted_items)
        self.lbl_preview_title.configure(
            text=f"Топ-{count} новостей" if count > 0 else "Новости не найдены"
        )
        self.render_news_items(formatted_items)
        self.set_progress(1.0, f"Собрано: {count} нов. ({now_short})")

    def _handle_export_pdf_clicked(self) -> None:
        """Обработчик нажатия кнопки «Скачать PDF» — сохраняет PDF-отчет на Рабочий стол."""
        if self._is_busy:
            return

        if self._on_export_pdf is not None:
            self._on_export_pdf()
            return

        selected = self.get_selected_coins()
        timeline = self.get_selected_timeline()
        if not selected:
            self.set_progress(0.0, "Выберите монеты для PDF!")
            return

        self._is_busy = True
        self.btn_export_pdf.configure(state="disabled", text="⏳  Генерация PDF...")
        self.set_progress(0.5, "Экспорт в PDF...")

        worker = threading.Thread(
            target=self._run_pdf_worker,
            args=(selected, timeline),
            daemon=True,
        )
        worker.start()

    def _run_pdf_worker(self, selected: list[str], timeline: str) -> None:
        """Фоновый поток генерации PDF на Рабочий стол."""
        try:
            # Если пользователь еще не нажимал «Сгенерировать рапорт», сначала соберем свежие данные
            if not self._current_prices and not self._current_news:
                data = collect_and_filter_data(selected_coins=selected, timeframe=timeline)
                self._current_prices = data.get("prices", {})
                self._current_news = data.get("news", [])

            pdf_path = export_report_to_pdf(
                prices=self._current_prices,
                news_items=self._current_news,
                selected_coins=selected,
                timeframe=timeline,
            )
            self.after(0, lambda p=pdf_path: self._on_pdf_finished(p, None))
        except Exception as exc:
            print(
                f"[PARSER ERROR] PDF Worker: {type(exc).__name__}: {exc}",
                file=sys.stderr,
                flush=True,
            )
            self.after(0, lambda e=exc: self._on_pdf_finished("", e))

    def _on_pdf_finished(self, pdf_path: str, error: Exception | None) -> None:
        """Обновляет UI после сохранения PDF на Рабочий стол."""
        self._is_busy = False
        self.btn_export_pdf.configure(state="normal", text="📄  Скачать PDF")

        if error is not None or not pdf_path:
            self.set_progress(0.0, "Ошибка сохранения PDF")
            return

        filename = os.path.basename(pdf_path)
        self.set_progress(1.0, f"PDF на Рабочем столе!")
        self.lbl_cache_badge.configure(text=f"PDF: {filename}")

    def _focus_report_view(self) -> None:
        """Возвращает фокус к основному режиму просмотра новостей."""
        if self._current_news:
            self.lbl_preview_title.configure(text=f"Топ-{len(self._current_news)} новостей")
        else:
            self.lbl_preview_title.configure(text="Топ-5 новостей")
            self._populate_initial_preview()

    def _open_working_directory(self) -> None:
        """Открывает рабочую директорию проекта в Проводнике Windows."""
        try:
            cwd = os.getcwd()
            if sys.platform.startswith("win"):
                os.startfile(cwd)  # noqa: S606
        except Exception as exc:
            print(
                f"[PARSER ERROR] System File Explorer: {type(exc).__name__}: {exc}",
                file=sys.stderr,
                flush=True,
            )

    def _show_system_info_in_preview(self) -> None:
        """Отображает краткую архитектурную справку в окне превью."""
        self.lbl_preview_title.configure(text="О системе Crypto Monitor & Report")
        info_items = [
            (
                "Архитектура автономного десктопного приложения",
                "Работает полностью локально без выделенных серверов и СУБД. Все котировки (CoinGecko) и RSS-ленты (CoinDesk, Cointelegraph, Decrypt) обрабатываются стандартными структурами Python (без Pandas) и сохраняются в перезаписываемый файл temp_data.json.",
                "Стек: Python  •  CustomTkinter  •  fpdf2 (UTF-8)  •  feedparser  •  requests",
            ),
            (
                "Экспорт PDF на Рабочий стол и сборка в .exe",
                "Итоговые PDF-отчеты автоматически сохраняются на Рабочий стол пользователя с поддержкой кириллических TTF-шрифтов.",
                "Статус: Полностью функциональное приложение",
            ),
        ]
        self.render_news_items(info_items)
