"""Tick positions and labels for every panel: nice breaks, shared limits, category axes."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import TYPE_CHECKING

import numpy as np
from matplotlib.collections import PathCollection
from matplotlib.ticker import FixedFormatter, FixedLocator, FuncFormatter

from hairline.errors import HairlineLayoutError
from hairline.layout.axes_style import (
    configure_ticks,
    data_interval,
    edge_alignment,
    is_numeric_axis,
    tick_formatter,
)
from hairline.layout.measure import text_width, wrap
from hairline.layout.styles import role_style
from hairline.numbers import format_number
from hairline.ticks import axis_limits, nice_breaks
from hairline.tokens import load_tokens

if TYPE_CHECKING:
    from hairline.figure import HairlineFigure


def tick_target(figure: HairlineFigure, which: str) -> int:
    """Target tick count from the panel grid: 5 for one row (column), 4 for two, 3 for more (same rule in R)."""
    count = figure.columns if which == "x" else math.ceil(len(figure.axes) / figure.columns)
    return {1: 5, 2: 4}.get(count, 3)


def current_limits(ax, which: str) -> tuple[float, float]:
    return tuple(ax.get_ylim() if which == "y" else ax.get_xlim())


def tick_interval(figure: HairlineFigure, index: int, which: str) -> tuple[float, float] | None:
    """Data range for automatic limits, or None once the user (or a zoom) has set the limits."""
    ax, key = figure.axes[index], (index, which)
    if key not in figure.auto_limits:
        figure.auto_limits[key] = ax.get_autoscaley_on() if which == "y" else ax.get_autoscalex_on()
    applied = figure.applied_limits.get(key)
    if applied is not None and not all(math.isclose(a, b) for a, b in zip(applied, current_limits(ax, which),
                                                                          strict=True)):
        figure.auto_limits[key] = False
    if not figure.auto_limits[key]:
        return None
    shared = figure.sharey if which == "y" else figure.sharex
    return data_interval(figure.axes if shared else [ax], which)


def names_axis(labels: Sequence[str]) -> bool:
    """Labels with a letter are names, read like every other name in ink; numbers (years, lane 1, 2, …) stay
    faint with the other tick labels."""
    return any(character.isalpha() for label in labels for character in label)


def set_categories(ax, which: str, names: list[str]) -> list[str]:
    axis = ax.yaxis if which == "y" else ax.xaxis
    axis.set_major_locator(FixedLocator(range(len(names))))
    axis.set_major_formatter(FixedFormatter(names))
    return names


def hour_breaks(low: float, high: float, target: int) -> list[float]:
    """Whole hours in [low, high] at the smallest step of `time_axis.steps` that gives at most `target` ticks."""
    for step in load_tokens()["time_axis"]["steps"]:
        breaks = [float(hour) for hour in range(math.ceil(low / step) * step, math.floor(high) + 1, step)]
        if len(breaks) <= target:
            return breaks
    return [low, high]


def hour_label(value: float, _position: object = None) -> str:
    """'06', '18', and past midnight '02' again."""
    return f"{int(round(value)) % 24:02d}"


def time_window(figure: HairlineFigure, index: int) -> tuple[float, float]:
    """The hours shown: the panel's own, else its data plus a margin; panels sharing x share the widest."""
    from hairline.charts.time_of_day import hour_window
    panels = [key for key in figure.time_hours if figure.sharex or key == index]
    given = [figure.time_hours[key] for key in panels if figure.time_hours[key] is not None]
    if given:
        return min(low for low, _ in given), max(high for _, high in given)
    low, high = data_interval([figure.axes[key] for key in panels], "x")
    return hour_window([low], [high], load_tokens()["time_axis"]["margin_hours"])


def configure_time_ticks(figure: HairlineFigure, index: int) -> list[str]:
    ax, (low, high) = figure.axes[index], time_window(figure, index)
    ax.set_xlim(low, high, auto=False)
    breaks = hour_breaks(low, high, {1: load_tokens()["time_axis"]["target"], 2: 5}.get(figure.columns, 4))
    ax.xaxis.set_major_locator(FixedLocator(breaks))
    ax.xaxis.set_major_formatter(FuncFormatter(hour_label))
    return [hour_label(value) for value in breaks]


def wrapped_names(figure: HairlineFigure, ax, names: list[str], y_labels: Sequence[str]) -> list[str]:
    """Names on an x axis, each wrapped to its slot (the plot's estimated width over the axis range, less the label
    gap), so neighbours never meet. A word wider than its slot cannot be placed: the figure is refused with what
    would fit (same rule in R)."""
    style = role_style(figure.settings, "label")
    low, high = sorted(ax.get_xlim())
    if not names or high <= low:
        return names
    gap = load_tokens()["ticks"]["label_rows_gap"] * style["size"]
    slot = estimated_plot_width(figure, y_labels) / (high - low) - gap
    lines = [wrap(name.replace("\n", " "), style["family"], style["size"], style["weight"], slot) for name in names]
    widest = max(text_width(line, style["family"], style["size"], style["weight"]) for wrapped in lines
                 for line in wrapped)
    if widest > slot + 1e-6:
        raise HairlineLayoutError(
            f"hairline: the {len(names)} names on the x axis do not fit side by side: a word needs {widest:.0f} pt "
            f"and each name has {max(slot, 0):.0f} pt; use a wider size, fewer groups, or a chart that lists the "
            f"groups as rows (bars, spread, ridgeline, dotplot)")
    return ["\n".join(wrapped) for wrapped in lines]


def estimated_plot_width(figure: HairlineFigure, y_labels: Sequence[str]) -> float:
    """A panel's plot width before the layout: the figure's width less its margins, the gaps between columns and the
    y labels with their gap (same estimate in R)."""
    spacing, base = load_tokens()["spacing"], figure.settings.base_size
    style = role_style(figure.settings, "label")
    usable = figure.figure.get_size_inches()[0] * 72 - 2 * spacing["margin"] * base
    column = (usable - (figure.columns - 1) * spacing["panel_columns"] * base) / figure.columns
    labels = max((text_width(label, style["family"], style["size"]) for label in y_labels), default=0.0)
    return column - (labels + spacing["y_labels_plot"] * base if labels else 0.0)


def labels_fit(breaks: list[float], labels: list[str], limits: tuple[float, float], width: float,
               figure: HairlineFigure) -> bool:
    """Whether neighbouring x labels keep `ticks.label_rows_gap` between them: each centred on its break, or
    aligned inward at the plot's edges, as they are drawn."""
    style = role_style(figure.settings, "label")
    gap = load_tokens()["ticks"]["label_rows_gap"] * style["size"]
    low, high = limits
    spans = []
    for value, label in zip(breaks, labels, strict=True):
        offset, size = (value - low) / (high - low), text_width(label, style["family"], style["size"])
        start = offset * width - size * {"left": 0.0, "right": 1.0}.get(edge_alignment(offset), 0.5)
        spans.append((start, start + size))
    return all(second[0] - first[1] >= gap for first, second in zip(spans, spans[1:], strict=False))


def fitting_target(figure: HairlineFigure, interval: tuple[float, float], percent: bool, whole: bool,
                   margin: float, target: int, y_labels: Sequence[str]) -> int:
    """The largest tick target, from the panel grid's down to three, whose x labels stand apart on the plot's
    estimated width (same rule in R)."""
    width = estimated_plot_width(figure, y_labels)
    for candidate in range(target, 2, -1):
        breaks = nice_breaks(*interval, target=candidate, whole=whole)
        formatter = tick_formatter(breaks, percent, figure.settings.locale)
        if labels_fit(breaks, [formatter(value) for value in breaks], axis_limits(*interval, breaks, margin), width,
                      figure):
            return candidate
    return 3


def mark_half_size(ax) -> float:
    """Half the size, in pt, of the largest mark with a size of its own: a scatter dot or a line's marker (a
    censor tick); 0 without such marks."""
    dots = [float(np.sqrt(item.get_sizes().max())) / 2 for item in ax.collections
            if isinstance(item, PathCollection) and len(item.get_offsets()) and len(item.get_sizes())]
    markers = [line.get_markersize() / 2 for line in ax.lines if line.get_marker() not in (None, "", "None", "none")]
    return max(dots + markers, default=0.0)


def mark_margin(figure: HairlineFigure, axes) -> float:
    """The share of an axis the largest mark's half-size takes on the least plot height: data that close to an
    outer break widens the axis by it, so no mark is cut by the plot's edge (same rule in R)."""
    half = max((mark_half_size(ax) for ax in axes), default=0.0)
    least = load_tokens()["spacing"]["min_plot_height"] * figure.settings.base_size
    return half / least


def integer_breaks(low: float, high: float) -> list[float]:
    """Whole-number ticks from the lowest to the highest whole number in range, at most six of them."""
    first, last = math.ceil(low - 1e-9), math.floor(high + 1e-9)
    step = next(step for step in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000) if (last - first) / step <= 5)
    return [float(value) for value in range(first, last + 1, step)]


def configure_all_ticks(figure: HairlineFigure) -> list[list[str]]:
    labels = []
    for index, ax in enumerate(figure.axes):
        if index in figure.bare_panels:
            labels.append([])
            continue
        for which in ("y", "x"):
            if which == "x" and index in figure.time_hours:
                configure_time_ticks(figure, index)
                figure.applied_limits[(index, which)] = current_limits(ax, which)
                continue
            if (index, which) in figure.integer_axes:
                low, high = current_limits(ax, which)
                axis = ax.yaxis if which == "y" else ax.xaxis
                axis.set_major_locator(FixedLocator(integer_breaks(low, high)))
                axis.set_major_formatter(FuncFormatter(lambda value, _position=None: format_number(
                    value, 0, figure.settings.locale)))
                if which == "y":
                    labels.append([format_number(value, 0, figure.settings.locale)
                                   for value in integer_breaks(low, high)])
                continue
            if (index, which) in figure.category_axes:
                if which == "x":
                    figure.category_axes[(index, which)] = wrapped_names(figure, ax, figure.category_axes[
                        (index, which)], labels[-1] if labels else [])
                result = set_categories(ax, which, figure.category_axes[(index, which)])
                if names_axis(result):
                    ax.tick_params(axis=which, labelcolor=figure.settings.neutral["ink"])
                if which == "y":
                    labels.append(result)
                continue
            percent = (index, which) in figure.percent_axes
            shared = figure.sharey if which == "y" else figure.sharex
            interval, whole = tick_interval(figure, index, which), (index, which) in figure.whole_axes
            margin = mark_margin(figure, figure.axes if shared else [ax])
            target = tick_target(figure, which)
            if which == "x" and interval is not None and is_numeric_axis(ax.xaxis):
                target = fitting_target(figure, interval, percent, whole, margin, target, labels[-1])
            result = configure_ticks(ax, which, interval, percent, figure.settings.locale, target, margin, whole)
            figure.applied_limits[(index, which)] = current_limits(ax, which)
            if which == "y":
                labels.append(result)
    return labels


