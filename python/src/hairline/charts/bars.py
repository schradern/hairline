"""Bar chart: counts or sums per category, side by side or stacked, vertical or horizontal, values at the ends."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

from hairline import entities
from hairline.charts.common import check_columns, humanise, with_counts
from hairline.charts.correlation_geometry import text_color
from hairline.figure import HairlineFigure, figure
from hairline.marks import lone_color
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


def value_text(value: float, percent: bool) -> str:
    locale = current_settings().locale
    return format_percent(value, 0, locale) if percent else format_number(value, 0, locale)


def value_label(ax, value: float, position: tuple[float, float], horizontal: bool, percent: bool,
                gid: str = "hairline-value") -> None:
    settings = current_settings()
    gap = load_tokens()["bars"]["label_gap"] * role_size(settings, "label")
    ax.annotate(value_text(value, percent), xy=position, xytext=(gap, 0) if horizontal else (0, gap),
                textcoords="offset points", ha="left" if horizontal else "center",
                va="center" if horizontal else "bottom", fontsize=role_size(settings, "label"),
                color=settings.neutral["muted"], fontfamily=settings.font, annotation_clip=False, gid=gid)


def segment_label(ax, value: float, centre: tuple[float, float], color: str, percent: bool) -> None:
    """The segment's value in its middle, in ink or surface, whichever contrasts more with the fill."""
    settings = current_settings()
    ax.text(*centre, value_text(value, percent), ha="center", va="center", fontsize=role_size(settings, "label"),
            color=text_color(color, {"neutral": settings.neutral}), fontfamily=settings.font, gid="hairline-segment")


def stacked_labels(ax, spots: list[float], base: list[float], heights: list[float], color: str, options: dict) -> None:
    smallest = load_tokens()["bars"]["segment_min"] * options["largest"]
    for spot, low, height in zip(spots, base, heights, strict=True):
        if height >= smallest and height > 0:
            middle = low + height / 2
            segment_label(ax, height, (middle, spot) if options["horizontal"] else (spot, middle), color,
                          options["percent"])


def draw_bars(ax, table: pd.DataFrame, names: list[str], groups: list[str], options: dict) -> None:
    category, value, by = options["category"], options["value"], options["by"]
    rules, horizontal, stacked = load_tokens()["bars"], options["horizontal"], options["stacked"]
    positions = [len(names) - 1 - index if horizontal else index for index in range(len(names))]
    base, single = [0.0] * len(names), rules["width"] if stacked else rules["width"] / len(groups)
    edge = {"edgecolor": current_settings().neutral["surface"], "linewidth": rules["gap_pt"] / 2} if stacked else \
        {"linewidth": 0}
    options = {**options, "largest": max_total(table, category, value, by, names, groups, options)}
    ends = 0.0
    for index, group in enumerate(groups):
        heights = bar_values(table, category, value, by, names, group, options["percent"])
        step = (len(groups) - 1) / 2 - index if horizontal else index - (len(groups) - 1) / 2
        offset = 0.0 if stacked else step * single
        color = entities.color(group) if by else lone_color()
        where = [position + offset for position in positions]
        draw = ax.barh if horizontal else ax.bar
        draw(where, heights, single * 0.92, base, color=color, label=group if by else "_nolegend_", **edge)
        ends = max([ends, *heights])
        if stacked and options["labels"]:
            stacked_labels(ax, where, base, heights, color, options)
        elif options["labels"]:
            for spot, height in zip(where, heights, strict=True):
                value_label(ax, height, (height, spot) if horizontal else (spot, height), horizontal,
                            options["percent"])
        if stacked:
            base = [low + height for low, height in zip(base, heights, strict=True)]
    if stacked and options["labels"] and not options["percent"]:
        for spot, total in zip(positions, base, strict=True):
            value_label(ax, total, (total, spot) if horizontal else (spot, total), horizontal, False,
                        "hairline-total")
    if options["labels"] and not (stacked and options["percent"]):
        reach = (max(base) if stacked else ends) * (1 + rules["label_headroom"])
        ax.update_datalim([(reach, positions[0])] if horizontal else [(positions[0], reach)])


def max_total(table: pd.DataFrame, category: str, value: str, by: str | None, names: list[str], groups: list[str],
              options: dict) -> float:
    if options["percent"]:
        return 1.0
    if options["stacked"]:
        return float(table.groupby(category)[value].sum().max())
    return float(table[value].max())


def bars(data: pd.DataFrame, category: str, value: str | None = None, by: str | None = None, *,
         title: str | None = None, subtitle: str | None = None, caption: str | None = None, stacked: bool = False,
         percent: bool = False, horizontal: bool | None = None, sort: str | None = None,
         order: Sequence[str] | None = None, labels: bool = True, colors: Mapping[str, str] | None = None,
         size: str = "onehalf") -> HairlineFigure:
    """Bars per category; without `value` rows are counted. Long or many labels turn the bars horizontal;
    single series are sorted by value unless `order` or `sort="given"` says otherwise."""
    data, value = with_counts(data, value)
    check_columns(data, [category, value, by])
    table, names, groups = bar_table(data, category, value, by, order,
                                     sort or ("given" if by and not stacked else "value"))
    horizontal = is_long(names) if horizontal is None else horizontal
    split = f" and {str(by).replace('_', ' ')}" if by and by != category else ""
    result = figure(title or f"{humanise(value)} by {str(category).replace('_', ' ')}{split}", subtitle=subtitle,
                    caption=caption, size=size)
    with entities.chart(groups if by else [], colors):
        draw_bars(result.ax, table, names, groups, {"category": category, "value": value, "by": by,
                                                    "horizontal": horizontal, "stacked": stacked, "percent": percent,
                                                    "labels": labels})
    result.categories(0, list(reversed(names)) if horizontal else names, "y" if horizontal else "x")
    pad = load_tokens()["bars"]["category_pad"]
    (result.ax.set_ylim if horizontal else result.ax.set_xlim)(-pad, len(names) - 1 + pad)
    if percent:
        result.percent_axis(0, "x" if horizontal else "y")
    if by:
        result.legend()
    return result
