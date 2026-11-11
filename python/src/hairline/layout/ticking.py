"""Tick positions and labels for every panel: nice breaks, shared limits, category axes."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import TYPE_CHECKING

import numpy as np
from matplotlib.collections import PathCollection
from matplotlib.ticker import FixedFormatter, FixedLocator, FuncFormatter

from hairline.layout.axes_style import configure_ticks, data_interval
from hairline.numbers import format_number
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
                result = set_categories(ax, which, figure.category_axes[(index, which)])
                if names_axis(result):
                    ax.tick_params(axis=which, labelcolor=figure.settings.neutral["ink"])
                if which == "y":
                    labels.append(result)
                continue
            percent = (index, which) in figure.percent_axes
            shared = figure.sharey if which == "y" else figure.sharex
            result = configure_ticks(ax, which, tick_interval(figure, index, which), percent,
                                     figure.settings.locale, tick_target(figure, which),
                                     mark_margin(figure, figure.axes if shared else [ax]),
                                     (index, which) in figure.whole_axes)
            figure.applied_limits[(index, which)] = current_limits(ax, which)
            if which == "y":
                labels.append(result)
    return labels


