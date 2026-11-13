"""Легковесный генератор графиков цен на базе Pillow (PIL.ImageDraw) без тяжелого matplotlib."""

from __future__ import annotations

from datetime import datetime, timezone
import math
import os
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from src.pdf_exporter import resolve_resource_path


def _load_pil_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Загружает системный или ресурсный TTF-шрифт для подписей на графике."""
    candidates = (
        [
            resolve_resource_path(os.path.join("assets", "fonts", "arialbd.ttf")),
            r"C:\Windows\Fonts\segoeuib.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
        ]
        if bold
        else [
            resolve_resource_path(os.path.join("assets", "fonts", "arial.ttf")),
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arial.ttf",
        ]
    )
    for path in candidates:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _format_price_label(val: float) -> str:
    """Форматирует цену для осей и заголовка графика."""
    if val >= 1000:
        return f"${val:,.0f}"
    if val >= 10:
        return f"${val:,.2f}"
    return f"${val:,.4f}"


def _format_time_tick(ts: float, timeframe: str) -> str:
    """Форматирует метку времени оси X в зависимости от выбранного периода."""
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    tf = (timeframe or "").lower()
    if "недел" in tf or "7 дн" in tf or "месяц" in tf or "30 дн" in tf or tf in ("7d", "30d"):
        return dt.strftime("%d.%m")
    return dt.strftime("%H:%M")


def render_price_charts_image(
    price_history: dict[str, list[dict[str, float]]],
    selected_coins: list[str],
    timeframe: str,
    theme: str = "dark",
    width: int = 920,
    row_height: int = 210,
) -> Image.Image | None:
    """
    Строит сводное изображение с графиками цен для выбранных монет за указанный период.
    Поддерживает две темы: 'dark' (для превью в GUI) и 'light' (для вставки в PDF).
    """
    coins = [c for c in selected_coins if price_history.get(c)]
    if not coins:
        coins = [c for c, pts in price_history.items() if len(pts) >= 2]
    if not coins:
        return None

    num_coins = len(coins)
    cols = 1 if num_coins == 1 else 2
    rows = math.ceil(num_coins / cols)

    # Рендерим с 2x сглаживанием (Supersampling) для идеальной четкости линий и текста
    scale = 2
    W = width * scale
    H = (rows * row_height + 16) * scale

    is_dark = theme == "dark"
    bg_canvas = (7, 16, 28, 255) if is_dark else (255, 255, 255, 255)
    card_bg = (11, 23, 39, 255) if is_dark else (246, 249, 253, 255)
    card_border = (27, 50, 78, 255) if is_dark else (212, 222, 235, 255)
    grid_color = (22, 41, 64, 255) if is_dark else (226, 234, 244, 255)
    text_main = (236, 244, 255, 255) if is_dark else (20, 32, 50, 255)
    text_muted = (130, 152, 178, 255) if is_dark else (100, 115, 135, 255)

    img = Image.new("RGBA", (W, H), bg_canvas)
    draw = ImageDraw.Draw(img, "RGBA")

    font_title = _load_pil_font(14 * scale, bold=True)
    font_price = _load_pil_font(13 * scale, bold=True)
    font_axis = _load_pil_font(10 * scale, bold=False)

    pad = 10 * scale
    cell_w = (W - pad * (cols + 1)) // cols
    cell_h = (H - pad * (rows + 1)) // rows
    period_short = timeframe.replace("Timeline: ", "").strip() or "За 24 часа"

    for idx, ticker in enumerate(coins):
        r = idx // cols
        c = idx % cols
        # Если последняя карточка нечетная, растягиваем ее на всю ширину
        is_last_single = (idx == num_coins - 1) and (num_coins % 2 == 1) and (cols == 2)
        cur_cell_w = (cell_w * 2 + pad) if is_last_single else cell_w

        x0 = pad + c * (cell_w + pad)
        y0 = pad + r * (cell_h + pad)
        x1 = x0 + cur_cell_w
        y1 = y0 + cell_h

        # Рамка карточки графика
        draw.rounded_rectangle(
            [x0, y0, x1, y1],
            radius=8 * scale,
            fill=card_bg,
            outline=card_border,
            width=1 * scale,
        )

        series = price_history.get(ticker, [])
        if len(series) < 2:
            continue

        prices_list = [pt["price"] for pt in series]
        ts_list = [pt["ts"] for pt in series]
        min_p = min(prices_list)
        max_p = max(prices_list)
        first_p = prices_list[0]
        last_p = prices_list[-1]
        pct_change = ((last_p - first_p) / first_p * 100.0) if first_p else 0.0

        is_up = pct_change >= 0
        line_color = (44, 229, 255, 255) if (is_up and is_dark) else (
            (16, 165, 95, 255) if is_up else (244, 63, 94, 255)
        )
        fill_color = (44, 229, 255, 42) if (is_up and is_dark) else (
            (16, 165, 95, 38) if is_up else (244, 63, 94, 42)
        )
        badge_color = (56, 232, 165, 255) if is_up else (255, 92, 118, 255)
        if not is_dark:
            badge_color = (16, 135, 75, 255) if is_up else (200, 40, 55, 255)

        # Заголовок карточки: Тикер + Период слева, Цена + % справа
        header_y = y0 + 10 * scale
        draw.text(
            (x0 + 14 * scale, header_y),
            f"{ticker}/USD  •  {period_short}",
            font=font_title,
            fill=text_main,
        )

        sign = "+" if pct_change >= 0 else ""
        right_label = f"{_format_price_label(last_p)}  ({sign}{pct_change:.2f}%)"
        bbox = draw.textbbox((0, 0), right_label, font=font_price)
        rw = bbox[2] - bbox[0]
        draw.text(
            (x1 - 14 * scale - rw, header_y + 1 * scale),
            right_label,
            font=font_price,
            fill=badge_color,
        )

        # Область построения кривой
        plot_left = x0 + 64 * scale
        plot_right = x1 - 16 * scale
        plot_top = y0 + 40 * scale
        plot_bottom = y1 - 28 * scale
        plot_w = max(10, plot_right - plot_left)
        plot_h = max(10, plot_bottom - plot_top)

        # Горизонтальные линии сетки и подписи цен (Min, Mid, Max)
        p_span = max_p - min_p
        if p_span <= 0:
            p_span = max(last_p * 0.01, 0.0001)

        for level_ratio, level_val in ((0.0, max_p), (0.5, (max_p + min_p) / 2.0), (1.0, min_p)):
            gy = int(plot_top + level_ratio * plot_h)
            draw.line([(plot_left, gy), (plot_right, gy)], fill=grid_color, width=1 * scale)
            lbl = _format_price_label(level_val)
            draw.text((x0 + 10 * scale, gy - 6 * scale), lbl, font=font_axis, fill=text_muted)

        # Координаты точек графика
        coords: list[tuple[int, int]] = []
        n_pts = len(prices_list)
        for i, p_val in enumerate(prices_list):
            px = int(plot_left + (i / (n_pts - 1)) * plot_w)
            norm_y = (p_val - min_p) / p_span
            py = int(plot_bottom - norm_y * plot_h)
            coords.append((px, py))

        # Заливка под графиком
        poly_pts = [(plot_left, plot_bottom), *coords, (plot_right, plot_bottom)]
        draw.polygon(poly_pts, fill=fill_color)

        # Линия графика
        draw.line(coords, fill=line_color, width=int(2.5 * scale), joint="curve")

        # Точка текущей цены в конце графика
        last_x, last_y = coords[-1]
        r_dot = 3 * scale
        draw.ellipse([last_x - r_dot, last_y - r_dot, last_x + r_dot, last_y + r_dot], fill=line_color)

        # Подписи времени по оси X (начало, середина, конец)
        for tick_idx in (0, n_pts // 2, n_pts - 1):
            tx = int(plot_left + (tick_idx / (n_pts - 1)) * plot_w)
            t_str = _format_time_tick(ts_list[tick_idx], timeframe)
            tb = draw.textbbox((0, 0), t_str, font=font_axis)
            tw = tb[2] - tb[0]
            tx_clamped = max(plot_left, min(plot_right - tw, tx - tw // 2))
            draw.text((tx_clamped, plot_bottom + 6 * scale), t_str, font=font_axis, fill=text_muted)

    # Уменьшаем в 2 раза с LANCZOS-фильтром для идеального сглаживания
    final_img = img.resize((width, rows * row_height + 16), resample=Image.Resampling.LANCZOS)
    return final_img.convert("RGB")
