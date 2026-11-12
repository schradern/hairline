"""Ridgeline plot: one density ridge per group on a shared x-axis, overlapping the row above, medians marked."""

from __future__ import annotations

import math
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
from hairline.charts.comparisons import section_comparisons
from hairline.charts.options import Reference, apply_options, references, sorted_groups
from hairline.charts.spread_geometry import DIAMOND, OPEN_EDGE
from hairline.charts.summaries import (
    CENTRES,
    STAT_NAMES,
    as_names,
    check_summary,
    measure_numbers,
    stat_pairs,
    summary_legend,
    summary_values,
)
from hairline.charts.timeseries import groups_of
from hairline.charts.tips import pairs_tip, tip_measures
from hairline.figure import HairlineFigure, figure
from hairline.layout.geometry import load_font_metrics
from hairline.marks import STATIC_ID
from hairline.numbers import format_number
from hairline.settings import current_settings
from hairline.stats.density import density
from hairline.tokens import load_tokens

RIDGE_ID, MEDIAN_ID = "hairline-ridge", "hairline-median"
WHY = "A ridge shows its own spread; raincloud() and spread() draw intervals"


def draw_ridge(ax, curve: tuple[list[float], list[float]], base: float, scale: float, color: str,
               layer: float) -> list[dict]:
    """A surface-coloured shape hiding the ridges behind, the light fill and the outline in the group colour;
    returns the fill and outline in data units, for the ridge's tooltip targets."""
    settings, rules = current_settings(), load_tokens()["ridgeline"]
    grid, height = curve
    outline = [(x, base + value * scale) for x, value in zip(grid, height, strict=True)]
    corners = [(grid[0], base), *outline, (grid[-1], base)]
    ax.add_patch(Polygon(corners, closed=True, facecolor=settings.neutral["surface"], edgecolor="none", linewidth=0,
                         zorder=layer, gid="hairline-occluder"))
    ax.add_patch(Polygon(corners, closed=True, facecolor=color, alpha=rules["fill_opacity"], edgecolor="none",
                         linewidth=0, zorder=layer + 0.001, gid=RIDGE_ID))
    xs, ys = zip(*outline, strict=True)
    width = load_tokens()["lines"]["data"] * settings.base_size
    ax.plot(xs, ys, color=color, linewidth=width, zorder=layer + 0.002, label="_nolegend_", gid=STATIC_ID)
    return [{"polygon": corners, "alpha": rules["fill_opacity"]}, {"line": outline, "width": width}]


def draw_centres(ax, values: np.ndarray, curve: tuple[list[float], list[float]], base: float, scale: float,
                 layer: float, marks: Sequence[str], color: str) -> tuple[list[dict], tuple[float, float] | None]:
    """The median as a line from the baseline up to the ridge, the mean as an open diamond on the ridge's outline;
    both held within the ridge. Returns them in data units, for the tooltip targets, and the median's top."""
    settings, tokens = current_settings(), load_tokens()
    found, shapes, top = summary_values(values), [], None

    def on_ridge(value: float) -> tuple[float, float]:
        x = min(max(value, curve[0][0]), curve[0][-1])
        return x, base + float(np.interp(x, curve[0], curve[1])) * scale
    if "median" in marks:
        top = on_ridge(found["median"])
        line = tokens["reference"]["width"] * settings.base_size
        ax.plot([top[0], top[0]], [base, top[1]], color=settings.neutral["ink"], zorder=layer + 0.003, linewidth=line,
                gid=MEDIAN_ID, label="_nolegend_")
        shapes.append({"line": [(top[0], base), top], "width": line, "color": settings.neutral["ink"]})
    if "mean" in marks:
        width = tokens["lines"]["data"] * settings.base_size
        radius = DIAMOND * tokens["lines"]["point_radius"] * settings.base_size
        centre = on_ridge(found["mean"])
        ax.plot([centre[0]], [centre[1]], marker="D", markersize=radius * math.sqrt(2), linestyle="none",
                markerfacecolor=settings.neutral["surface"], markeredgecolor=color, markeredgewidth=width * OPEN_EDGE,
                zorder=layer + 0.004, gid=MEDIAN_ID, label="_nolegend_")
        shapes.append({"diamond": centre, "r": radius, "color": settings.neutral["surface"], "edge": color,
                       "edge_width": width * OPEN_EDGE})
    return shapes, top


def draw_spikes(ax, values: np.ndarray, base: float, color: str, layer: float) -> list[dict]:
    """A group too small or too uniform for a density (one value, or all alike) shows each value as a spike, so
    its row is never empty; returns the spikes in data units."""
    width = load_tokens()["lines"]["data"] * current_settings().base_size
    height, shapes = load_tokens()["ridgeline"]["spike"], []
    for value in sorted(set(np.asarray(values, dtype=float))):
        ax.plot([value, value], [base, base + height], color=color, zorder=layer + 0.002, label="_nolegend_",
                linewidth=width, gid=STATIC_ID)
        shapes.append({"line": [(value, base), (value, base + height)], "width": width})
    return shapes


def ridge_anchor(shapes: list[dict], top: tuple[float, float] | None) -> tuple[float, float]:
    """Where a ridge's tooltip points: the top of its median line, else the highest point of its outline (or of
    its spikes)."""
    if top is not None:
        return top
    points = [point for shape in shapes if "line" in shape for point in shape["line"]]
    return max(points, key=lambda point: point[1])


def draw_ridges(ax, groups: list, curves: list, scale: float, marks: Sequence[str], palette: dict[str, str],
                statistics: list) -> dict[str, dict]:
    """Top row first, so each lower ridge is drawn in front of the one above. Returns each ridge drawn: its marks
    in data units and where its tooltip points."""
    drawn = {}
    for index, ((name, values), curve, (_, counted)) in enumerate(zip(groups, curves, statistics, strict=True)):
        base, layer = float(len(groups) - 1 - index), 1 + index * 0.01
        top = None
        if curve is None:
            shapes = draw_spikes(ax, values, base, palette[name], layer)
        else:
            shapes = draw_ridge(ax, curve, base, scale, palette[name], layer)
            if len(counted):
                centres, top = draw_centres(ax, counted, curve, base, scale, layer, marks, palette[name])
                shapes += centres
        if shapes:
            drawn[name] = {"marks": shapes, "at": ridge_anchor(shapes, top)}
    return drawn


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


def ridge_rows(panels: list[list], measures: Sequence[str], every: np.ndarray, percent: bool, compare: str | None,
               marks: Sequence[str], locale: str) -> tuple[list[dict], dict, str | None]:
    """Every ridge's measures as key-number pairs and, with `compare`, its Δ and p against the reference or the
    ridge above, within its panel; the values by row key; and the caption note naming the test."""
    numbers = measure_numbers(every, percent, None)
    rows = [{"name": f"{index}\x1f{name}", "section": index, "count": len(groups), "position": position,
             "pairs": stat_pairs(values, measures, numbers, locale=locale) if len(values) else []}
            for index, groups in enumerate(panels) for position, (name, values) in enumerate(groups)]
    values = {f"{index}\x1f{name}": data for index, groups in enumerate(panels) for name, data in groups}
    note = section_comparisons(rows, values, compare, marks, numbers, "ridgeline",
                               {key: key.split("\x1f", 1)[1] for key in values})
    return rows, values, note


def ridge_numbers(panels: list[list], stats: Sequence[str], every: np.ndarray, percent: bool, compare: str | None,
                  marks: Sequence[str], locale: str) -> tuple[list[list[tuple[float, str, str]]], str | None]:
    """Each panel's numbers column: every ridge's measures and, with `compare`, its Δ and p, at its baseline (a
    group without values in a panel has none); and the caption note naming the test."""
    rows, values, note = ridge_rows(panels, stats, every, percent, compare, marks, locale)
    columns = [[(float(row["count"] - 1 - row["position"]), label, text) for row in rows
                if row["section"] == index and len(values[row["name"]]) for label, text in row["pairs"]]
               for index in range(len(panels))]
    return columns, note


def ridge_tips(panels: list[list], stats: Sequence[str], every: np.ndarray, percent: bool, compare: str | None,
               marks: Sequence[str], locale: str) -> list[dict[str, str]]:
    """Each panel's ridge tooltips by group: the marks it draws and the numbers beside it, its n, and its Δ and p
    with `compare`, in the numbers column's digits; a group without values in a panel has none."""
    rows, values, _ = ridge_rows(panels, tip_measures(marks, stats), every, percent, compare, marks, locale)
    return [{row["name"].split("\x1f", 1)[1]: pairs_tip(row["name"].split("\x1f", 1)[1], row["pairs"])
             for row in rows if row["section"] == index and len(values[row["name"]])} for index in range(len(panels))]


def ridgeline(data: pd.DataFrame, group: str, value: str, *, title: str | None = None, subtitle: str | None = None,
              caption: str | None = None, order: Sequence[str] | None = None, medians: bool = True,
              colors: Mapping[str, str] | None = None, size: str = "onehalf", show_n: bool = False,
              min_n: int | None = None, clip: float | tuple[float | None, float | None] | None = None,
              clip_stats: bool = False, color_by: str | None = None,
              dimension: str | None = None, sort: str | None = None, percent: bool = False,
              x_title: str | None = None, reference: Reference = None,
              highlight: Sequence[str] | str | None = None, key_title: str | None = None, facet: str | None = None,
              columns: int | None = None, summary: str | Sequence[str] | None = None,
              stats: str | Sequence[str] = (), compare: str | None = None) -> HairlineFigure:
    """Distributions per group as overlapping ridges, the first group on top; all ridges share one height scale.
    `show_n` writes each group's n after its name; `min_n`, `clip`, `color_by` and `dimension` work as in
    `spread()`: groups too small are named in the caption, and so are the values clipped off. Shared with the
    other charts: `sort` ("median", "mean", "n"), `percent`, `x_title`, `reference` (lines on the value axis),
    `highlight` (groups kept in colour), `key_title` and `facet` (one panel per value, in `columns` columns, on
    shared axes and one height scale; with `show_n` each panel's n in its header).

    `summary` chooses the marks on each ridge: "median" (a line up to the ridge) and "mean" (an open diamond on
    its outline); by default the median, or nothing with `medians=False`. A summary you give is named in the
    legend. A ridge shows its own spread, so intervals belong to raincloud() or spread(). `stats` writes measures
    beside each ridge, in a column right of the plot: any of "median", "mean", "iqr", "range", "sd", "ci", "n".
    `compare` adds each ridge's difference against one group or the ridge above ("adjacent"), with its 95 % CI and
    p, to that column (within each panel); the caption names the test, which follows the centre as in spread()."""
    check_columns(data, [group, value, color_by, facet])
    check_present(data, value, "ridgeline")
    check_numeric(data, [value], "ridgeline")
    marks = (("median",) if medians else ()) if summary is None else check_summary(summary, "ridgeline", CENTRES, WHY)
    stats = as_names(stats, "ridgeline", "stats", STAT_NAMES)
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
    statistics = drawn if clip_stats else counted
    numbers, compared = ridge_numbers(statistics, stats, every, percent, compare, marks, locale)
    tips = ridge_tips(statistics, stats, every, percent, compare, marks, locale)
    notes = [small, clip_caption(every, limits, clip_stats, locale) if clip is not None else None, compared]
    result = figure(title or f"{humanise(value)} by {str(group).replace('_', ' ')}", subtitle=subtitle,
                    caption=with_caption(caption, *notes), size=size, panels=len(panels),
                    layout="grid" if facet else "rows", columns=columns or (min(len(panels), 2) if facet else 1))
    palette, coarse = series_colors(names, data, group, color_by, colors, dimension, "ridgeline", highlight,
                                    named=True)
    labels = labels_with_n(names, {name: len(values) for name, values in groups}, locale) \
        if show_n and not facet else names
    for index, panel in enumerate(panels):
        ridges = draw_ridges(result.axes[index], drawn[index], curves[index], scale, marks, palette,
                             statistics[index])
        for name, ridge in ridges.items():
            tip = [{"at": ridge["at"], "text": tips[index][name]}] if name in tips[index] else []
            result.target(index, name, palette[name], ridge["marks"], tip)
        frame_panel(result, index, panel, labels, statistics[index], show_n, percent, label_room(reference))
        if numbers[index]:
            result.numbers_column(index, numbers[index])
    legend = [("square", color, label) for label, color in
              dict.fromkeys((coarse[name], palette[name]) for name in names)] if color_by else []
    legend += summary_legend(marks, "tick", current_settings().neutral["ink"], locale) if summary is not None else []
    if legend:
        result.legend(legend)
    return apply_options(result, "ridgeline", names=names, x_title=x_title or humanise(value), reference=reference,
                         reference_axis="x", key_title=key_title)
