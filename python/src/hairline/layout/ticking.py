"""Tick positions and labels for every panel: nice breaks, shared limits, category axes."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from matplotlib.ticker import FixedFormatter, FixedLocator

from hairline.layout.axes_style import configure_ticks, data_interval

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


def set_categories(ax, which: str, names: list[str]) -> list[str]:
    axis = ax.yaxis if which == "y" else ax.xaxis
    axis.set_major_locator(FixedLocator(range(len(names))))
    axis.set_major_formatter(FixedFormatter(names))
    return names


def configure_all_ticks(figure: HairlineFigure) -> list[list[str]]:
    labels = []
    for index, ax in enumerate(figure.axes):
        if index in figure.bare_panels:
            labels.append([])
            continue
        for which in ("y", "x"):
            if (index, which) in figure.category_axes:
                result = set_categories(ax, which, figure.category_axes[(index, which)])
                if which == "y":
                    labels.append(result)
                continue
            percent = which == "y" and index in figure.percent_axes
            result = configure_ticks(ax, which, tick_interval(figure, index, which), percent,
                                     figure.settings.locale, tick_target(figure, which))
            figure.applied_limits[(index, which)] = current_limits(ax, which)
            if which == "y":
                labels.append(result)
    return labels


