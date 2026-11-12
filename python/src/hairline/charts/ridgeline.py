"""Ridgeline plot: one density ridge per group on a shared x-axis, overlapping the row above, medians marked."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd
from matplotlib.patches import Polygon

from hairline.charts.common import (
    check_columns,
    check_numeric,
    check_present,
    clip_caption,
    clip_limits,
    drop_small,
    humanise,
    labels_with_n,
    series_colors,
    with_caption,
    within,
)
from hairline.charts.options import Reference, apply_options, references, sorted_groups
from hairline.charts.timeseries import groups_of
from hairline.figure import HairlineFigure, figure
from hairline.layout.geometry import load_font_metrics
from hairline.marks import STATIC_ID
from hairline.numbers import format_number
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


def draw_median(ax, values: np.ndarray, curve: tuple[list[float], list[float]], base: float, scale: float,
                layer: float) -> None:
    settings = current_settings()
    middle = min(max(quantiles(values, [0.5])[0], curve[0][0]), curve[0][-1])
    top = base + float(np.interp(middle, curve[0], curve[1])) * scale
    ax.plot([middle, middle], [base, top], color=settings.neutral["ink"], zorder=layer + 0.003,
            linewidth=load_tokens()["reference"]["width"] * settings.base_size, gid=MEDIAN_ID, label="_nolegend_")


def draw_spikes(ax, values: np.ndarray, base: float, color: str, layer: float) -> None:
    """A group too small or too uniform for a density (one value, or all alike) shows each value as a spike, so
    its row is never empty."""
    settings = current_settings()
    height = load_tokens()["ridgeline"]["spike"]
    for value in sorted(set(np.asarray(values, dtype=float))):
        ax.plot([value, value], [base, base + height], color=color, zorder=layer + 0.002, label="_nolegend_",
                linewidth=load_tokens()["lines"]["data"] * settings.base_size, gid=STATIC_ID)


def draw_ridges(ax, groups: list, curves: list, scale: float, medians: bool, palette: dict[str, str],
                statistics: list) -> None:
    """Top row first, so each lower ridge is drawn in front of the one above."""
    for index, ((name, values), curve, (_, counted)) in enumerate(zip(groups, curves, statistics, strict=True)):
        base, layer = float(len(groups) - 1 - index), 1 + index * 0.01
        if curve is None:
            draw_spikes(ax, values, base, palette[name], layer)
            continue
        draw_ridge(ax, curve, base, scale, palette[name], layer)
        if medians:
            draw_median(ax, counted, curve, base, scale, layer)


def panel_groups(rows_of: dict, names: list[str], value: str, facet: str | None, panel: str | None) -> list:
    """Each group's values in one panel (all of them without a facet); a group absent here has none."""
    def values_in(rows: pd.DataFrame) -> np.ndarray:
        rows = rows if panel is None else rows[rows[facet].astype(str) == panel]
        return rows[value].dropna().astype(float).to_numpy()
    return [(name, values_in(rows_of[name])) for name in names]


def label_room(reference: Reference) -> float:
    """The share of the plot height a reference label hangs into from the top (its gap, cap height and gap at the
    caption size), on the least plot height, so the top ridge stays clear of it; 0 without labels."""
    if not any(label for _, label in references(reference, "ridgeline")):
        return 0.0
    tokens = load_tokens()
    label = tokens["type"]["roles"]["caption"]["factor"] * (2 * tokens["reference"]["label_gap"]
                                                            + load_font_metrics().cap_height)
    return label / tokens["spacing"]["min_plot_height"]


def frame_panel(result: HairlineFigure, index: int, panel: str | None, labels: list[str], statistics: list,
                show_n: bool, percent: bool, room: float) -> None:
    """A panel's group rows, its header with the n of the values counted (a facet's panel) and its value axis, with
    `room` (a share of it) above the top ridge for reference labels."""
    rules = load_tokens()["ridgeline"]
    result.categories(index, list(reversed(labels)), "y")
    result.axes[index].set_ylim(0, (len(labels) + rules["overlap"] + rules["headroom"]) / (1 - room))
    if panel is not None:
        total = sum(len(values) for _, values in statistics)
        stats = [("n", format_number(total, 0, current_settings().locale))] if show_n else ()
        result.panel_header(index, panel, stats=stats)
    if percent:
        result.percent_axis(index, "x")


def ridgeline(data: pd.DataFrame, group: str, value: str, *, title: str | None = None, subtitle: str | None = None,
              caption: str | None = None, order: Sequence[str] | None = None, medians: bool = True,
              colors: Mapping[str, str] | None = None, size: str = "onehalf", show_n: bool = False,
              min_n: int | None = None, clip: float | tuple[float | None, float | None] | None = None,
              clip_stats: bool = False, color_by: str | None = None,
              dimension: str | None = None, sort: str | None = None, percent: bool = False,
              x_title: str | None = None, reference: Reference = None,
              highlight: Sequence[str] | str | None = None, key_title: str | None = None, facet: str | None = None,
              columns: int | None = None) -> HairlineFigure:
    """Distributions per group as overlapping ridges, the first group on top; all ridges share one height scale.
    `show_n` writes each group's n after its name; `min_n`, `clip`, `color_by` and `dimension` work as in
    `spread()`: groups too small are named in the caption, and so are the values clipped off. Shared with the
    other charts: `sort` ("median", "mean", "n"), `percent`, `x_title`, `reference` (lines on the value axis),
    `highlight` (groups kept in colour), `key_title` and `facet` (one panel per value, in `columns` columns, on
    shared axes and one height scale; with `show_n` each panel's n in its header)."""
    check_columns(data, [group, value, color_by, facet])
    check_present(data, value, "ridgeline")
    check_numeric(data, [value], "ridgeline")
    locale = current_settings().locale
    rules = load_tokens()["ridgeline"]
    framed = groups_of(data, group, order, "ridgeline")
    groups = [(name, rows[value].dropna().astype(float).to_numpy()) for name, rows in framed]
    groups, small = drop_small(groups, min_n, "ridgeline", locale)
    groups = sorted_groups(groups, sort, "ridgeline")
    names = [name for name, _ in groups]
    every = np.concatenate([values for _, values in groups])
    limits = clip_limits(every, clip, "ridgeline")
    panels = [panel for panel, _ in groups_of(data, facet, None, "ridgeline")] if facet else [None]
    rows_of = dict(framed)
    counted = [panel_groups(rows_of, names, value, facet, panel) for panel in panels]
    drawn = [[(name, within(values, limits)) for name, values in here] for here in counted]
    curves = [[density(values) for _, values in here] for here in drawn]
    peak = max((max(curve[1]) for here in curves for curve in here if curve), default=1.0)
    scale = (1 + rules["overlap"]) / peak
    notes = [small, clip_caption(every, limits, clip_stats, locale) if clip is not None else None]
    result = figure(title or f"{humanise(value)} by {str(group).replace('_', ' ')}", subtitle=subtitle,
                    caption=with_caption(caption, *notes), size=size, panels=len(panels),
                    layout="grid" if facet else "rows", columns=columns or (min(len(panels), 2) if facet else 1))
    palette, coarse = series_colors(names, data, group, color_by, colors, dimension, "ridgeline", highlight)
    labels = labels_with_n(names, {name: len(values) for name, values in groups}, locale) \
        if show_n and not facet else names
    for index, panel in enumerate(panels):
        statistics = drawn[index] if clip_stats else counted[index]
        draw_ridges(result.axes[index], drawn[index], curves[index], scale, medians, palette, statistics)
        frame_panel(result, index, panel, labels, statistics, show_n, percent, label_room(reference))
    if color_by:
        result.legend([("square", color, label) for label, color in
                       dict.fromkeys((coarse[name], palette[name]) for name in names)])
    return apply_options(result, "ridgeline", names=names, x_title=x_title or humanise(value), reference=reference,
                         reference_axis="x", key_title=key_title)
