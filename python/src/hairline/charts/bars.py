"""Bar chart: counts or sums per category, side by side or stacked, vertical or horizontal, values at the ends."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import pandas as pd

from hairline import entities
from hairline.charts.common import (
    check_columns,
    check_labels,
    check_numeric,
    check_present,
    group_names,
    humanise,
    ordered_names,
    with_counts,
)
from hairline.charts.correlation_geometry import text_color
from hairline.drawing import measure_for
from hairline.figure import HairlineFigure, figure
from hairline.fonts import families
from hairline.marks import lone_color
from hairline.numbers import auto_digits, format_compact, format_percent, number_unit
from hairline.settings import current_settings, role_size
from hairline.tokens import load_tokens


def bar_table(data: pd.DataFrame, category: str, value: str, by: str | None, order: Sequence[str] | None,
              sort: str) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Sums per category (and group), the category order and the group order. A cell whose values are all missing
    stays missing (no bar, label or tooltip); for sorting and percent totals it counts as zero."""
    columns = list(dict.fromkeys([category] + ([by] if by else [])))
    check_labels(data, columns, "bars")
    check_present(data, value, "bars")
    check_numeric(data, [value], "bars")
    names = ordered_names(data[category], order or None, "bars", category)
    groups = group_names(data[by]) if by else [""]
    table = data.groupby(columns, sort=False, observed=True)[value].sum(min_count=1).reset_index()
    table[category] = table[category].astype(str)
    if sort == "value" and not order:
        totals = table.groupby(category, sort=False)[value].sum()
        names = sorted(names, key=lambda name: -totals[name])
    return table, names, groups


def is_long(names: Sequence[str]) -> bool:
    rules = load_tokens()["bars"]
    return len(names) > rules["horizontal_count"] or max(len(name) for name in names) > rules["horizontal_length"]


def fits_upright(names: Sequence[str], values: Sequence[str], bars_per_slot: int, width_pt: float,
                 settings) -> bool:
    """Upright bars need every category name, and every value over its bar, to fit the room a category gets across
    the plot (the figure's width less its margins and the y labels, about as wide as the widest value), with
    `bars.label_space` x the base size between neighbours; otherwise the bars lie down."""
    rules, spacing, base, measure = load_tokens()["bars"], load_tokens()["spacing"], settings.base_size, \
        measure_for(settings)
    widest = max((measure(text, "label") for text in values), default=0.0)
    plot = width_pt - 2 * spacing["margin"] * base - widest - spacing["y_labels_plot"] * base
    slot = plot / (len(names) - 1 + 2 * rules["category_pad"])
    space = rules["label_space"] * base
    return max(measure(name, "label") for name in names) <= slot - space and widest <= slot / bars_per_slot - space


def upright_values(table: pd.DataFrame, category: str, value: str, by: str | None, names: list[str],
                   groups: list[str], options: dict) -> list[str]:
    """The value texts upright bars would carry over their ends: every bar's, or each stack's total."""
    if not options["labels"] or (options["stacked"] and options["percent"]):
        return []
    heights = [bar_values(table, category, value, by, names, group, options["percent"]) for group in groups]
    numbers = bar_numbers(table, category, value, by, names, groups, options)
    if options["stacked"]:
        heights = [[sum(without_missing(list(column))) for column in zip(*heights, strict=True)]]
    return [value_text(height, options["percent"], numbers) for row in heights for height in row
            if not math.isnan(height)]


def bar_numbers(table: pd.DataFrame, category: str, value: str, by: str | None, names: list[str], groups: list[str],
                options: dict) -> tuple[int, tuple[float, str] | None]:
    """Decimals and unit of the values on the bars: the data's own decimals, or, from 10^9 on, one short-scale
    unit for the chart (1.2 tn, 0.8 tn) with `numbers.compact_digits` decimals."""
    heights = [height for group in groups for height in bar_values(table, category, value, by, names, group, False)]
    if options["stacked"]:
        heights += list(table.groupby(category)[value].sum())
    unit = number_unit(heights, current_settings().locale)
    return (load_tokens()["numbers"]["compact_digits"], unit) if unit else \
        (auto_digits(table[value].to_numpy(dtype=float)), None)


def is_horizontal(table: pd.DataFrame, names: list[str], groups: list[str], options: dict, result) -> bool:
    """Many or long labels lie down, and so do labels too wide for upright bars at this figure's width."""
    if is_long(names):
        return True
    values = upright_values(table, options["category"], options["value"], options["by"], names, groups, options)
    width = result.figure.get_size_inches()[0] * 72
    return not fits_upright(names, values, 1 if options["stacked"] else len(groups), width, result.settings)


def bar_values(table: pd.DataFrame, category: str, value: str, by: str | None, names: list[str], group: str,
               percent: bool) -> list[float]:
    rows = table if not by else table[table[by].astype(str) == group]
    totals = table.groupby(category)[value].sum()
    if percent:
        check_percent_values(table, category, value)
        check_percent_totals(totals, names)
    sums = rows.groupby(category)[value].sum(min_count=1)
    return [float(sums.get(name, 0.0)) / (float(totals[name]) if percent else 1.0) for name in names]


def without_missing(heights: list[float]) -> list[float]:
    """Heights for stacking and reach: a missing bar takes no room."""
    return [0.0 if math.isnan(height) else height for height in heights]


def check_percent_values(table: pd.DataFrame, category: str, value: str) -> None:
    """Shares are parts of a whole: a negative part would draw below zero and push the others past 100 %."""
    negative = table[table[value] < 0]
    if len(negative):
        raise ValueError(f"hairline: bars: percent needs values of zero or more; {negative.iloc[0][category]!r} has "
                         f"{negative.iloc[0][value]:g}")


def check_percent_totals(totals: pd.Series, names: list[str]) -> None:
    empty = [name for name in names if not totals.get(name, 0.0) > 0]
    if empty:
        raise ValueError(f"hairline: bars: percent needs a total above zero in every category; {empty[0]!r} totals "
                         f"{totals.get(empty[0], 0.0):g}, so its shares are undefined")


def value_text(value: float, percent: bool, numbers: tuple[int, tuple[float, str] | None] = (0, None)) -> str:
    """A bar's value: whole percentages, or the data's own decimals (0.12 stays 0.12, counts stay whole), in the
    chart's unit when its numbers are that large (see bar_numbers)."""
    locale = current_settings().locale
    return format_percent(value, 0, locale) if percent else format_compact(value, *numbers, locale)


def value_label(ax, value: float, position: tuple[float, float], horizontal: bool, percent: bool,
                gid: str = "hairline-value", numbers: tuple = (0, None)) -> None:
    settings = current_settings()
    gap = load_tokens()["bars"]["label_gap"] * role_size(settings, "label")
    ax.annotate(value_text(value, percent, numbers), xy=position, xytext=(gap, 0) if horizontal else (0, gap),
                textcoords="offset points", ha="left" if horizontal else "center",
                va="center" if horizontal else "bottom", fontsize=role_size(settings, "label"),
                color=settings.neutral["muted"], fontfamily=families(settings.font), annotation_clip=False, gid=gid)


def segment_label(ax, value: float, centre: tuple[float, float], color: str, percent: bool,
                  numbers: tuple = (0, None)) -> None:
    """The segment's value in its middle, in ink or surface, whichever contrasts more with the fill."""
    settings = current_settings()
    ax.text(*centre, value_text(value, percent, numbers), ha="center", va="center",
            fontsize=role_size(settings, "label"), color=text_color(color, {"neutral": settings.neutral}),
            fontfamily=families(settings.font), gid="hairline-segment")


def stacked_labels(ax, spots: list[float], base: list[float], heights: list[float], color: str, options: dict) -> None:
    smallest = load_tokens()["bars"]["segment_min"] * options["largest"]
    for spot, low, height in zip(spots, base, heights, strict=True):
        if height >= smallest and height > 0:
            middle = low + height / 2
            segment_label(ax, height, (middle, spot) if options["horizontal"] else (spot, middle), color,
                          options["percent"], options["numbers"])


def draw_bars(ax, table: pd.DataFrame, names: list[str], groups: list[str], options: dict) -> None:
    category, value, by = options["category"], options["value"], options["by"]
    rules, horizontal, stacked = load_tokens()["bars"], options["horizontal"], options["stacked"]
    positions = [len(names) - 1 - index if horizontal else index for index in range(len(names))]
    single = rules["width"] if stacked else rules["width"] / len(groups)
    ups, downs = [0.0] * len(names), [0.0] * len(names)
    edge = {"edgecolor": current_settings().neutral["surface"], "linewidth": rules["gap_pt"] / 2} if stacked else \
        {"linewidth": 0}
    options = {**options, "largest": max_total(table, category, value, by, names, groups, options),
               "numbers": bar_numbers(table, category, value, by, names, groups, options)}
    ends, present = 0.0, [False] * len(names)
    for index, group in enumerate(groups):
        heights = bar_values(table, category, value, by, names, group, options["percent"])
        step = (len(groups) - 1) / 2 - index if horizontal else index - (len(groups) - 1) / 2
        offset = 0.0 if stacked else step * single
        color = entities.color(group) if by else lone_color()
        where = [position + offset for position in positions]
        draw = ax.barh if horizontal else ax.bar
        base = [up if height >= 0 else down for up, down, height in zip(ups, downs, heights, strict=True)] \
            if stacked else [0.0] * len(names)
        draw(where, heights, single * 0.92, base, color=color, label=group if by else "_nolegend_", **edge)
        ends = max([ends, *without_missing(heights)])
        present = [shown or not math.isnan(height) for shown, height in zip(present, heights, strict=True)]
        if stacked and options["labels"]:
            stacked_labels(ax, where, base, heights, color, options)
        elif options["labels"]:
            for spot, height in zip(where, heights, strict=True):
                if not math.isnan(height):
                    value_label(ax, height, (height, spot) if horizontal else (spot, height), horizontal,
                                options["percent"], numbers=options["numbers"])
        ups = [up + max(height, 0.0) for up, height in zip(ups, without_missing(heights), strict=True)]
        downs = [down + min(height, 0.0) for down, height in zip(downs, without_missing(heights), strict=True)]
    if stacked and options["labels"] and not options["percent"]:
        shown = [index for index, value in enumerate(present) if value]
        stacked_totals(ax, [positions[index] for index in shown], [ups[index] for index in shown],
                       [downs[index] for index in shown], horizontal, options["numbers"])
    if options["labels"] and not (stacked and options["percent"]):
        reach = (max(ups) if stacked else ends) * (1 + rules["label_headroom"])
        ax.update_datalim([(reach, positions[0])] if horizontal else [(positions[0], reach)])


def stacked_totals(ax, positions: list[float], ups: list[float], downs: list[float], horizontal: bool,
                   numbers: tuple) -> None:
    """The signed total at the end of the stack: past the positive segments, or the negative ones if none is
    positive. Negative segments stack below zero, positive ones above."""
    for spot, up, down in zip(positions, ups, downs, strict=True):
        end = up if up > 0 else down
        value_label(ax, up + down, (end, spot) if horizontal else (spot, end), horizontal, False, "hairline-total",
                    numbers)


def max_total(table: pd.DataFrame, category: str, value: str, by: str | None, names: list[str], groups: list[str],
              options: dict) -> float:
    if options["percent"]:
        return 1.0
    if options["stacked"]:
        return float(table[value].clip(lower=0).groupby(table[category]).sum().max())
    return float(table[value].max())


def bars(data: pd.DataFrame, category: str, value: str | None = None, by: str | None = None, *,
         title: str | None = None, subtitle: str | None = None, caption: str | None = None, stacked: bool = False,
         percent: bool = False, horizontal: bool | None = None, sort: str | None = None,
         order: Sequence[str] | None = None, labels: bool = True, colors: Mapping[str, str] | None = None,
         size: str = "onehalf") -> HairlineFigure:
    """Bars per category; without `value` rows are counted. Long or many labels, or labels too wide for upright
    bars at the figure's width, turn the bars horizontal; single series are sorted by value unless `order` or
    `sort="given"` says otherwise."""
    data, value = with_counts(data, value)
    check_columns(data, [category, value, by])
    stacked = stacked and by is not None
    if (sort or "value") not in ("value", "given"):
        raise ValueError(f"hairline: bars: sort {sort!r} must be 'value' or 'given'")
    table, names, groups = bar_table(data, category, value, by, order,
                                     sort or ("given" if by and not stacked else "value"))
    split = f" and {str(by).replace('_', ' ')}" if by and by != category else ""
    result = figure(title or f"{humanise(value)} by {str(category).replace('_', ' ')}{split}", subtitle=subtitle,
                    caption=caption, size=size)
    options = {"category": category, "value": value, "by": by, "stacked": stacked, "percent": percent,
               "labels": labels}
    if horizontal is None:
        horizontal = is_horizontal(table, names, groups, options, result)
    with entities.chart(groups if by else [], colors):
        draw_bars(result.ax, table, names, groups, {**options, "horizontal": horizontal})
    result.categories(0, list(reversed(names)) if horizontal else names, "y" if horizontal else "x")
    pad = load_tokens()["bars"]["category_pad"]
    (result.ax.set_ylim if horizontal else result.ax.set_xlim)(-pad, len(names) - 1 + pad)
    if percent:
        result.percent_axis(0, "x" if horizontal else "y")
    if by:
        result.legend()
    return result
