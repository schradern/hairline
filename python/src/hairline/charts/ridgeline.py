"""Ridgeline plot: one density ridge per group on a shared x-axis, overlapping the row above, medians marked."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd
from matplotlib.patches import Polygon

from hairline import entities
from hairline.charts.common import check_columns, check_numeric, check_present, humanise
from hairline.charts.timeseries import groups_of
from hairline.figure import HairlineFigure, figure
from hairline.marks import STATIC_ID
from hairline.settings import current_settings
from hairline.stats.density import density, quantiles
from hairline.tokens import load_tokens

RIDGE_ID, MEDIAN_ID = "hairline-ridge", "hairline-median"


def draw_ridge(ax, curve: tuple[list[float], list[float]], base: float, scale: float, color: str, layer: float) -> None:
    """A surface-coloured shape hiding the ridges behind, the light fill and the outline in the group colour."""
    settings, rules = current_settings(), load_tokens()["ridgeline"]
    grid, height = curve
    outline = [(x, base + value * scale) for x, value in zip(grid, height, strict=True)]
    corners = [(grid[0], base), *outline, (grid[-1], base)]
    ax.add_patch(Polygon(corners, closed=True, facecolor=settings.neutral["surface"], edgecolor="none", linewidth=0,
                         zorder=layer, gid="hairline-occluder"))
    ax.add_patch(Polygon(corners, closed=True, facecolor=color, alpha=rules["fill_opacity"], edgecolor="none",
                         linewidth=0, zorder=layer + 0.001, gid=RIDGE_ID))
    xs, ys = zip(*outline, strict=True)
    ax.plot(xs, ys, color=color, linewidth=load_tokens()["lines"]["data"] * settings.base_size, zorder=layer + 0.002,
            label="_nolegend_", gid=STATIC_ID)


def draw_median(ax, values: pd.Series, curve: tuple[list[float], list[float]], base: float, scale: float,
                layer: float) -> None:
    settings = current_settings()
    middle = quantiles(values, [0.5])[0]
    top = base + float(np.interp(middle, curve[0], curve[1])) * scale
    ax.plot([middle, middle], [base, top], color=settings.neutral["ink"], zorder=layer + 0.003,
            linewidth=load_tokens()["reference"]["width"] * settings.base_size, gid=MEDIAN_ID, label="_nolegend_")


def draw_spikes(ax, values: pd.Series, base: float, color: str, layer: float) -> None:
    """A group too small or too uniform for a density (one value, or all alike) shows each value as a spike, so
    its row is never empty."""
    settings = current_settings()
    height = load_tokens()["ridgeline"]["spike"]
    for value in sorted(set(values.astype(float))):
        ax.plot([value, value], [base, base + height], color=color, zorder=layer + 0.002, label="_nolegend_",
                linewidth=load_tokens()["lines"]["data"] * settings.base_size, gid=STATIC_ID)


def draw_ridges(ax, groups: list, curves: list, scale: float, value: str, medians: bool) -> None:
    """Top row first, so each lower ridge is drawn in front of the one above."""
    for index, ((name, rows), curve) in enumerate(zip(groups, curves, strict=True)):
        base, layer = float(len(groups) - 1 - index), 1 + index * 0.01
        if curve is None:
            draw_spikes(ax, rows[value].dropna(), base, entities.color(name), layer)
            continue
        draw_ridge(ax, curve, base, scale, entities.color(name), layer)
        if medians:
            draw_median(ax, rows[value].dropna(), curve, base, scale, layer)


def ridgeline(data: pd.DataFrame, group: str, value: str, *, title: str | None = None, subtitle: str | None = None,
              caption: str | None = None, order: Sequence[str] | None = None, medians: bool = True,
              colors: Mapping[str, str] | None = None, size: str = "onehalf") -> HairlineFigure:
    """Distributions per group as overlapping ridges, the first group on top; all ridges share one height scale."""
    check_columns(data, [group, value])
    check_present(data, value, "ridgeline")
    check_numeric(data, [value], "ridgeline")
    rules, groups = load_tokens()["ridgeline"], groups_of(data, group, order, "ridgeline")
    curves = [density(rows[value].dropna()) for _, rows in groups]
    peak = max((max(curve[1]) for curve in curves if curve), default=1.0)
    scale = (1 + rules["overlap"]) / peak
    result = figure(title or f"{humanise(value)} by {str(group).replace('_', ' ')}", subtitle=subtitle,
                    caption=caption, size=size)
    with entities.chart([name for name, _ in groups], colors):
        draw_ridges(result.ax, groups, curves, scale, value, medians)
    result.categories(0, [name for name, _ in reversed(groups)], "y")
    result.ax.set_ylim(0, len(groups) + rules["overlap"] + rules["headroom"])
    result.x_title(humanise(value))
    return result
