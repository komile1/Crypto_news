"""Модуль генерации PDF-отчетов на базе fpdf2 с поддержкой кириллицы (UTF-8 / TTF)."""

from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Any

from fpdf import FPDF


def resolve_resource_path(relative_path: str) -> str:
    """Разрешает путь к ресурсам с поддержкой упаковки PyInstaller (sys._MEIPASS)."""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


def get_desktop_directory() -> str:
    """Возвращает путь к Рабочему столу пользователя через os.path.expanduser('~')."""
    home_dir = os.path.expanduser("~")
    for folder_name in ("Desktop", "Рабочий стол", "OneDrive\\Desktop", "OneDrive\\Рабочий стол"):
        candidate = os.path.join(home_dir, folder_name)
        if os.path.isdir(candidate):
            return candidate
    return home_dir


def _find_unicode_fonts() -> tuple[str | None, str | None]:
    """Ищет доступный TTF-шрифт с поддержкой кириллицы (в ресурсах проекта или системных шрифтах Windows)."""
    regular_candidates = [
        resolve_resource_path(os.path.join("assets", "fonts", "DejaVuSans.ttf")),
        resolve_resource_path(os.path.join("assets", "fonts", "arial.ttf")),
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    bold_candidates = [
        resolve_resource_path(os.path.join("assets", "fonts", "DejaVuSans-Bold.ttf")),
        resolve_resource_path(os.path.join("assets", "fonts", "arialbd.ttf")),
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\tahomabd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]

    reg_path = next((p for p in regular_candidates if os.path.isfile(p)), None)
    bold_path = next((p for p in bold_candidates if os.path.isfile(p)), None)
    if reg_path and not bold_path:
        bold_path = reg_path
    return reg_path, bold_path


class CryptoReportPDF(FPDF):
    """Минималистичный PDF-шаблон отчета Crypto Market Report с поддержкой UTF-8."""

    def __init__(self) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=16)
        self.font_family_name = "Helvetica"
        self._init_unicode_fonts()

    def _init_unicode_fonts(self) -> None:
        """Регистрирует TTF-шрифты для корректного отображения кириллицы и спецсимволов."""
        reg_path, bold_path = _find_unicode_fonts()
        if reg_path:
            try:
                self.add_font("CyrillicFont", style="", fname=reg_path)
                self.add_font("CyrillicFont", style="B", fname=bold_path or reg_path)
                self.font_family_name = "CyrillicFont"
            except Exception as exc:
                print(
                    f"[PARSER ERROR] PDF Font Load ({reg_path}): {type(exc).__name__}: {exc}",
                    file=sys.stderr,
                    flush=True,
                )

    def footer(self) -> None:
        """Нижний колонтитул с номером страницы."""
        self.set_y(-13)
        self.set_font(self.font_family_name, "", 8)
        self.set_text_color(130, 140, 155)
        self.cell(0, 8, f"Crypto Monitor & Report  •  Страница {self.page_no()}", align="C")


def export_report_to_pdf(
    prices: dict[str, dict[str, float]],
    news_items: list[dict[str, Any]],
    selected_coins: list[str],
    timeframe: str,
    output_path: str | None = None,
) -> str:
    """Генерирует PDF-отчет и сохраняет его на Рабочий стол пользователя."""
    pdf = CryptoReportPDF()
    pdf.add_page()
    ff = pdf.font_family_name

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    coins_label = ", ".join(selected_coins) if selected_coins else "Все монеты"
    period_label = timeframe.replace("Timeline: ", "").strip() or "За 24 часа"

    # 1. Шапка документа: Заголовок "Crypto Market Report"
    pdf.set_fill_color(11, 22, 36)
    pdf.rect(10, 10, 190, 26, style="F")

    pdf.set_xy(15, 14)
    pdf.set_font(ff, "B", 18)
    pdf.set_text_color(69, 240, 255)
    pdf.cell(0, 9, "Crypto Market Report", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(15)
    pdf.set_font(ff, "", 9)
    pdf.set_text_color(210, 225, 245)
    pdf.cell(
        0,
        6,
        f"Дата генерации: {now_str}   |   Активы: {coins_label}   |   Период: {period_label}",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.ln(8)

    # 2. Блок с текущими котировками (CoinGecko API)
    pdf.set_font(ff, "B", 13)
    pdf.set_text_color(20, 32, 48)
    pdf.cell(0, 8, "1. Актуальные рыночные котировки (USD)", new_x="LMARGIN", new_y="NEXT")

    pdf.set_draw_color(210, 220, 232)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    if prices:
        # Таблица котировок
        pdf.set_fill_color(238, 243, 250)
        pdf.set_font(ff, "B", 10)
        pdf.set_text_color(30, 45, 65)
        pdf.cell(45, 8, "Тикер", border=1, fill=True, align="C")
        pdf.cell(75, 8, "Цена (USD)", border=1, fill=True, align="C")
        pdf.cell(70, 8, "Изменение (24ч)", border=1, fill=True, align="C", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font(ff, "", 10)
        coins_to_show = [c for c in selected_coins if c in prices] or list(prices.keys())
        for ticker in coins_to_show:
            p_info = prices.get(ticker, {})
            usd_val = float(p_info.get("usd", 0.0))
            chg_val = float(p_info.get("change_24h", 0.0))

            price_str = f"${usd_val:,.2f}" if usd_val >= 1 else f"${usd_val:,.4f}"
            sign = "+" if chg_val >= 0 else ""
            chg_str = f"{sign}{chg_val:.2f}%"

            pdf.set_text_color(25, 35, 50)
            pdf.cell(45, 8, ticker, border=1, align="C")
            pdf.cell(75, 8, price_str, border=1, align="C")

            if chg_val > 0:
                pdf.set_text_color(16, 135, 75)
            elif chg_val < 0:
                pdf.set_text_color(195, 45, 45)
            else:
                pdf.set_text_color(90, 100, 115)

            pdf.cell(70, 8, chg_str, border=1, align="C", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_font(ff, "", 10)
        pdf.set_text_color(110, 120, 135)
        pdf.cell(0, 8, "Котировки временно недоступны (проверьте подключение к сети).", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)

    # 3. Блок отфильтрованных новостей
    pdf.set_font(ff, "B", 13)
    pdf.set_text_color(20, 32, 48)
    pdf.cell(
        0,
        8,
        f"2. Отфильтрованные новости ({len(news_items)})",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    if not news_items:
        pdf.set_font(ff, "", 10)
        pdf.set_text_color(110, 120, 135)
        pdf.multi_cell(
            0,
            6,
            "По выбранным монетам и временному периоду новостей не найдено.",
            new_x="LMARGIN",
            new_y="NEXT",
        )
    else:
        for idx, item in enumerate(news_items, start=1):
            title = item.get("title") or "Без заголовка"
            summary = item.get("summary") or ""
            source = item.get("source") or "RSS"
            pub_str = item.get("published_str") or ""
            matched = ", ".join(item.get("matched_coins") or [])
            tag_prefix = f"[{matched}] " if matched else ""

            # Заголовок новости
            pdf.set_font(ff, "B", 11)
            pdf.set_text_color(15, 35, 65)
            pdf.multi_cell(0, 6, f"{idx}. {tag_prefix}{title}", new_x="LMARGIN", new_y="NEXT")

            # Мета-строка (Источник и время публикации)
            pdf.set_font(ff, "", 8.5)
            pdf.set_text_color(110, 125, 145)
            meta_line = f"Источник: {source}   •   Опубликовано: {pub_str}"
            pdf.cell(0, 5, meta_line, new_x="LMARGIN", new_y="NEXT")

            # Краткое описание (очищенное от HTML)
            if summary:
                pdf.set_font(ff, "", 9.5)
                pdf.set_text_color(45, 55, 70)
                pdf.multi_cell(0, 5.2, summary, new_x="LMARGIN", new_y="NEXT")

            pdf.ln(3)

    # 4. Сохранение файла на Рабочий стол пользователя
    if output_path is None:
        desktop_dir = get_desktop_directory()
        file_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(desktop_dir, f"Crypto_Market_Report_{file_stamp}.pdf")

    try:
        pdf.output(output_path)
    except Exception as exc:
        print(
            f"[PARSER ERROR] PDF Save ({output_path}): {type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise

    return output_path
