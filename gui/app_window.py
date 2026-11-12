"""Главное окно приложения Crypto Monitor & Report на базе CustomTkinter."""

from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Callable

import customtkinter as ctk

from gui.theme import DEFAULT_COINS, PALETTE, TIMELINE_OPTIONS


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
        self._anim_after_id: str | None = None

        # Глобальная конфигурация темы
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Параметры окна
        self.title("Crypto Monitor & Report")
        self.geometry("1080x660")
        self.minsize(920, 580)
        self.configure(fg_color=PALETTE.bg_root)

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
        self.progress_bar.set(0.36)  # Начальное визуальное состояние как на референсе

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
            text="⚡ Рынок: BTC $91,420 (+2.4%)   •   ETH $3,180 (+1.1%)   •   SOL $194.50 (+4.8%)",
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
        """Заполняет окно превью стартовыми демонстрационными новостями в стиле референса."""
        sample_items = [
            (
                "1. [BTC] Институциональный приток в спотовые Bitcoin-ETF обновил недельный максимум",
                "Крупнейшие фонды зафиксировали чистый приток капитала на фоне стабилизации макроэкономических показателей и роста ликвидности.",
                "Источник: CoinDesk RSS  •  14 мин назад  •  Тикер: BTC",
            ),
            (
                "2. [SOL] Экосистема Solana обработала рекордный объем транзакций в DEX-протоколах",
                "Суточный объем торгов в децентрализованных пулах ликвидности вырос на 18%, комиссионные издержки остаются ниже $0.01.",
                "Источник: Cointelegraph RSS  •  42 мин назад  •  Тикер: SOL",
            ),
            (
                "3. [ETH] Разработчики Ethereum согласовали график оптимизации валидаторов в следующем обновлении",
                "Обновление направлено на снижение нагрузки на ноды и ускорение финализации блоков в периоды пиковой активности сети.",
                "Источник: Decrypt RSS  •  1 ч назад  •  Тикер: ETH",
            ),
            (
                "4. [BTC / Рынок] Аналитический обзор волатильности перед публикацией данных по инфляции",
                "Открытый интерес на фьючерсных рынках сохраняет нейтральный баланс, ключевые уровни поддержки удерживаются покупателями.",
                "Источник: CryptoSlate RSS  •  2 ч назад  •  Тикер: BTC",
            ),
            (
                "5. [SOL / DeFi] Новые стандарты безопасности для кросс-чейн мостов и агрегаторов ликвидности",
                "Аудиторские компании представили открытый чек-лист автоматического мониторинга смарт-контрактов в реальном времени.",
                "Источник: The Block RSS  •  3 ч назад  •  Тикер: SOL",
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
                "Нет новостей по выбранным фильтрам.\nВыберите хотя бы одну монету слева и нажмите «Сгенерировать рапорт».",
                "summary",
            )
        else:
            for headline, summary, meta in items:
                tb.insert("end", f"{headline}\n", "headline")
                tb.insert("end", f"{summary}\n", "summary")
                tb.insert("end", f"{meta}\n", "meta")

        self.preview_textbox.configure(state="disabled")

    def set_progress(self, value: float, status_text: str) -> None:
        """Обновляет индикатор прогресса (0.0 .. 1.0) и текстовый статус."""
        clamped = max(0.0, min(1.0, value))
        self.progress_bar.set(clamped)
        self.lbl_progress_status.configure(text=status_text)

    def _handle_generate_clicked(self) -> None:
        """Обработчик нажатия кнопки «Сгенерировать рапорт»."""
        selected = self.get_selected_coins()
        timeline = self.get_selected_timeline()

        if not selected:
            self.set_progress(0.0, "Выберите монеты!")
            self.render_news_items([])
            return

        if self._on_generate_report is not None:
            self._on_generate_report(selected, timeline)
            return

        # Демо-анимация прогресс-бара и фильтрации превью до подключения боевого парсера
        self.btn_generate.configure(state="disabled", text="Сбор данных...")
        self.set_progress(0.15, "Запрос RSS/API...")
        self._animate_demo_generation(selected, timeline, step=1)

    def _animate_demo_generation(self, selected: list[str], timeline: str, step: int) -> None:
        """Плавная визуальная обратная связь прогресс-бара при генерации рапорта."""
        if step == 1:
            self.set_progress(0.45, "Очистка HTML...")
            self._anim_after_id = self.after(
                180, lambda: self._animate_demo_generation(selected, timeline, 2)
            )
        elif step == 2:
            self.set_progress(0.80, "Запись JSON-кэша...")
            self._anim_after_id = self.after(
                180, lambda: self._animate_demo_generation(selected, timeline, 3)
            )
        else:
            now_str = datetime.now().strftime("%H:%M:%S")
            self.set_progress(1.0, f"Обновлено в {now_str}")
            self.lbl_cache_badge.configure(text=f"JSON Cache: {now_str}")
            self.btn_generate.configure(state="normal", text="Сгенерировать рапорт")
            self._populate_filtered_demo(selected, timeline)

    def _populate_filtered_demo(self, selected: list[str], timeline: str) -> None:
        """Фильтрует демо-новости по выбранным чекбоксам монет."""
        period_label = timeline.replace("Timeline: ", "")
        demo_db = [
            (
                "BTC",
                "[BTC] Биткоин удерживает ключевой уровень на фоне притока в спотовые ETF",
                "Объем торгов на спотовых площадках вырос на 14%, институциональные участники продолжают аккумуляцию актива.",
                f"Источник: CoinDesk RSS  •  Период: {period_label}",
            ),
            (
                "ETH",
                "[ETH] Активность в L2-сетях Ethereum достигла нового исторического максимума",
                "Суммарный TVL роллапов вырос благодаря снижению стоимости газа и запуску новых протоколов ликвидного стейкинга.",
                f"Источник: Decrypt RSS  •  Период: {period_label}",
            ),
            (
                "SOL",
                "[SOL] Сеть Solana демонстрирует рост числа активных адресов и DEX-оборота",
                "Высокая пропускная способность блокчейна привлекает новые потребительские приложения и платежные шлюзы.",
                f"Источник: Cointelegraph RSS  •  Период: {period_label}",
            ),
            (
                "BNB",
                "[BNB] Квартальное сжигание токенов BNB сократило оборотное предложение сети",
                "Автоматический механизм Auto-Burn успешно выполнен в BNB Chain, комиссионная активность остается стабильной.",
                f"Источник: Binance Blog RSS  •  Период: {period_label}",
            ),
            (
                "XRP",
                "[XRP] Трансграничные платежные коридоры расширяют интеграцию с банковскими шлюзами",
                "Новые партнерства в Азиатско-Тихоокеанском регионе увеличили суточную ликвидность пар с XRP.",
                f"Источник: CryptoSlate RSS  •  Период: {period_label}",
            ),
            (
                "LINK",
                "[LINK] Протокол кросс-чейн совместимости Chainlink CCIP интегрирован новыми DeFi-платформами",
                "Децентрализованные оракулы Chainlink расширили передачу верифицированных рыночных данных для токенизированных активов.",
                f"Источник: CoinDesk RSS  •  Период: {period_label}",
            ),
        ]

        filtered = [
            (f"{idx}. {title}", body, meta)
            for idx, (ticker, title, body, meta) in enumerate(
                [item for item in demo_db if item[0] in selected], start=1
            )
        ]
        self.lbl_preview_title.configure(text=f"Топ-{len(filtered)} новостей")
        self.render_news_items(filtered)

    def _handle_export_pdf_clicked(self) -> None:
        """Обработчик нажатия кнопки «Скачать PDF»."""
        if self._on_export_pdf is not None:
            self._on_export_pdf()
            return

        now_str = datetime.now().strftime("%H:%M:%S")
        self.set_progress(1.0, f"PDF готов ({now_str})")

    def _focus_report_view(self) -> None:
        """Возвращает фокус к основному режиму просмотра новостей."""
        self.lbl_preview_title.configure(text="Топ-5 новостей")
        self._populate_initial_preview()

    def _open_working_directory(self) -> None:
        """Открывает рабочую директорию проекта в Проводнике Windows."""
        try:
            cwd = os.getcwd()
            if sys.platform.startswith("win"):
                os.startfile(cwd)  # noqa: S606
        except Exception as exc:
            print(f"[PARSER ERROR] System File Explorer: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)

    def _show_system_info_in_preview(self) -> None:
        """Отображает краткую архитектурную справку в окне превью."""
        self.lbl_preview_title.configure(text="О системе Crypto Monitor & Report")
        info_items = [
            (
                "Архитектура автономного десктопного приложения",
                "Работает полностью локально без выделенных серверов и СУБД. Все котировки и RSS-ленты агрегируются через pandas и сохраняются в перезаписываемый временный JSON-кэш.",
                "Стек: Python  •  CustomTkinter  •  pandas  •  FPDF  •  feedparser  •  requests",
            ),
            (
                "Готовность к сборке в единый .exe (PyInstaller)",
                "Все пути к ресурсам и шрифтам разрешаются с поддержкой sys._MEIPASS, а экспортируемые PDF-рапорты сохраняются напрямую в рабочую папку пользователя.",
                "Статус: Интерфейс готов к подключению модулей src/",
            ),
        ]
        self.render_news_items(info_items)
