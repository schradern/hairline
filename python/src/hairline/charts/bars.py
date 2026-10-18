"""Bar chart: counts or sums per category, side by side or stacked, vertical or horizontal, values at the ends."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

from hairline import entities
from hairline.charts.common import check_columns, humanise, with_counts
from hairline.figure import HairlineFigure, figure
from hairline.numbers import format_number, format_percent
from hairline.settings import current_settings, role_size
from hairline.tokens import load_tokens


def bar_table(data: pd.DataFrame, category: str, value: str, by: str | None, order: Sequence[str] | None,
              sort: str) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Sums per category (and group), the category order and the group order."""
    columns = list(dict.fromkeys([category] + ([by] if by else [])))
    table = data.groupby(columns, sort=False, dropna=False)[value].sum().reset_index()
    table[category] = table[category].astype(str)
    names = list(order) if order else list(dict.fromkeys(table[category]))
    if sort == "value" and not order:
        totals = table.groupby(category, sort=False)[value].sum()
        names = sorted(names, key=lambda name: -totals[name])
    groups = list(dict.fromkeys(table[by].astype(str))) if by else [""]
    return table, names, groups


def is_long(names: Sequence[str]) -> bool:
    rules = load_tokens()["bars"]
    return len(names) > rules["horizontal_count"] or max(len(name) for name in names) > rules["horizontal_length"]


def bar_values(table: pd.DataFrame, category: str, value: str, by: str | None, names: list[str], group: str,
               percent: bool) -> list[float]:
    rows = table if not by else table[table[by].astype(str) == group]
    totals = table.groupby(category)[value].sum()
    sums = rows.groupby(category)[value].sum()
    return [float(sums.get(name, 0.0)) / (float(totals[name]) if percent else 1.0) for name in names]


def value_label(ax, value: float, position: tuple[float, float], horizontal: bool, percent: bool) -> None:
    settings = current_settings()
    text = format_percent(value, 0, settings.locale) if percent else format_number(value, 0, settings.locale)
    gap = load_tokens()["bars"]["label_gap"] * role_size(settings, "label")
    ax.annotate(text, xy=position, xytext=(gap, 0) if horizontal else (0, gap), textcoords="offset points",
                ha="left" if horizontal else "center", va="center" if horizontal else "bottom",
                fontsize=role_size(settings, "label"), color=settings.neutral["muted"], fontfamily=settings.font,
                annotation_clip=False)


def draw_bars(ax, table: pd.DataFrame, names: list[str], groups: list[str], options: dict) -> None:
    category, value, by = options["category"], options["value"], options["by"]
    width, horizontal, stacked = load_tokens()["bars"]["width"], options["horizontal"], options["stacked"]
    positions = [len(names) - 1 - index if horizontal else index for index in range(len(names))]
    base, single = [0.0] * len(names), width if stacked else width / len(groups)
    for index, group in enumerate(groups):
        heights = bar_values(table, category, value, by, names, group, options["percent"])
        offset = 0.0 if stacked else (index - (len(groups) - 1) / 2) * single
        color = entities.color(group) if by else current_settings().palette[0]
        where = [position + offset for position in positions]
        draw = ax.barh if horizontal else ax.bar
        draw(where, heights, single * 0.92, base, color=color, label=group if by else "_nolegend_", linewidth=0)
        if options["labels"] and not stacked:
            for spot, height in zip(where, heights, strict=True):
                value_label(ax, height, (height, spot) if horizontal else (spot, height), horizontal,
                            options["percent"])
        if stacked:
            base = [low + height for low, height in zip(base, heights, strict=True)]


def bars(data: pd.DataFrame, category: str, value: str | None = None, by: str | None = None, *,
         title: str | None = None, subtitle: str | None = None, caption: str | None = None, stacked: bool = False,
         percent: bool = False, horizontal: bool | None = None, sort: str | None = None,
         order: Sequence[str] | None = None, labels: bool = True, colors: Mapping[str, str] | None = None,
         size: str = "onehalf") -> HairlineFigure:
    """Bars per category; without `value` rows are counted. Long or many labels turn the bars horizontal;
    single series are sorted by value unless `order` or `sort="given"` says otherwise."""
    data, value = with_counts(data, value)
    check_columns(data, [category, value, by])
    table, names, groups = bar_table(data, category, value, by, order, sort or ("given" if by else "value"))
    horizontal = is_long(names) if horizontal is None else horizontal
    result = figure(title or f"{humanise(value)} by {str(category).replace('_', ' ')}", subtitle=subtitle,
                    caption=caption, size=size)
    with entities.chart(groups if by else [], colors):
        draw_bars(result.ax, table, names, groups, {"category": category, "value": value, "by": by,
                                                    "horizontal": horizontal, "stacked": stacked, "percent": percent,
                                                    "labels": labels})
    result.categories(0, list(reversed(names)) if horizontal else names, "y" if horizontal else "x")
    if percent and not horizontal:
        result.percent_axis(0)
    if by:
        result.legend()
    return result
