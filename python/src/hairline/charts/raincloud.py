"""Raincloud: per group a half density, the box (IQR and median) and the points, with
"n = …" under the group names and comparison brackets stacked without overlap."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd
from matplotlib.patches import Polygon, Rectangle

from hairline.charts.common import (
    check_columns,
    check_numeric,
    check_present,
    clip_caption,
    clip_limits,
    drop_small,
    humanise,
    series_colors,
    with_caption,
)
from hairline.charts.options import Reference, apply_options, sorted_groups
from hairline.charts.spread_geometry import DIAMOND, OPEN_EDGE
from hairline.charts.summaries import (
    BARS,
    SUMMARY_NAMES,
    as_names,
    check_summary,
    interval_of,
    measure_numbers,
    stat_pairs,
    summary_legend,
    summary_values,
)
from hairline.charts.timeseries import groups_of
from hairline.figure import HairlineFigure, figure
from hairline.fonts import families
from hairline.layout.geometry import load_font_metrics
from hairline.marks import FIXED_ID, STATIC_ID
from hairline.numbers import format_number, format_p, word
from hairline.settings import current_settings, role_size
from hairline.stats.density import density, jitter_offsets
from hairline.stats.tests import rank_sum
from hairline.tokens import load_tokens

DENSITY_ID = "hairline-density"
DEFAULT_SUMMARY = ("median", "iqr")
RANGE_LAYER = 0.9  # under the bars (patches draw at 1), so a slim bar shows over the range line
BRACKET_HEADROOM = 0.6  # bracket steps above the highest bracket, for its label


def bracket_levels(spans: Sequence[tuple[int, int]]) -> list[int]:
    """Lowest free level for each bracket, shorter brackets first, so no two brackets on a level overlap."""
    order = sorted(range(len(spans)), key=lambda index: (abs(spans[index][1] - spans[index][0]), index))
    levels, taken = [0] * len(spans), []
    for index in order:
        low, high = sorted(spans[index])
        level = 0
        while any(other_level == level and not (high < other_low or low > other_high)
                  for other_level, other_low, other_high in taken):
            level += 1
        levels[index] = level
        taken.append((level, low, high))
    return levels


def bracket_plot_height(levels: int) -> float | None:
    """The least plot height (x the base size) at which each of `levels` bracket levels has room for its p label:
    the label (pad, cap height and descender at the label size) above its bracket and clear of the next bracket's
    ticks, on a value axis spanning the data and the brackets, with room for the ticks' overshoot. None without
    brackets; never below `spacing.min_plot_height`."""
    if not levels:
        return None
    tokens, metrics = load_tokens(), load_font_metrics()
    rules, ticks = tokens["raincloud"], tokens["ticks"]
    label = tokens["type"]["roles"]["label"]["factor"] * (rules["label_pad"] + metrics.cap_height + metrics.descender)
    level = label / (1 - rules["bracket_tick"] / rules["bracket_step"])
    steps = 1 / rules["bracket_step"] + levels + BRACKET_HEADROOM
    overshoot = 1 + ticks["overshoot_low"] + ticks["overshoot_high"]
    return max(tokens["spacing"]["min_plot_height"], level * steps * overshoot)


def draw_group(ax, values: pd.Series, position: int, color: str, rules: dict, counted: pd.Series | None = None,
               marks: Sequence[str] = DEFAULT_SUMMARY) -> None:
    """Density and points of the values drawn; the summary marks of the values counted, quartiles held within the
    drawn range."""
    counted = values if counted is None else counted
    curve = density(values)
    if curve is not None:
        grid, height = curve
        peak, start = max(height), position + rules["density_offset"]
        outline = [(start + value / peak * rules["density_width"], level) for level, value in zip(grid, height,
                                                                                                    strict=True)]
        ax.add_patch(Polygon([(start, grid[0])] + outline + [(start, grid[-1])], closed=True, facecolor=color,
                             alpha=rules["density_opacity"], edgecolor="none", linewidth=0, gid=DENSITY_ID))
    draw_summary(ax, counted, (float(values.min()), float(values.max())), position, color, marks, rules)
    xs = [position + rules["points_centre"] + offset * rules["points_spread"] for offset in jitter_offsets(len(values))]
    ax.scatter(xs, values, color=color, label="_nolegend_", gid=STATIC_ID)


def draw_summary(ax, counted: pd.Series, drawn: tuple[float, float], position: int, color: str,
                 marks: Sequence[str], rules: dict) -> None:
    """At the box's place: the range as a thin line, the IQR as the box or an SD or CI as a slim bar, the median as
    a tick across it (in the surface colour on the box) and the mean as an open diamond."""
    settings, tokens = current_settings(), load_tokens()
    found, (low, high) = summary_values(counted), drawn
    width, half = tokens["lines"]["data"] * settings.base_size, rules["box_half"]

    def held(value: float) -> float:
        return min(max(value, low), high)
    if "range" in marks:
        ax.plot([position, position], [held(found["low"]), held(found["high"])], color=settings.neutral["faint"],
                linewidth=tokens["reference"]["width"] * settings.base_size, solid_capstyle="butt",
                label="_nolegend_", gid=FIXED_ID, zorder=RANGE_LAYER)
    bar = next((name for name in marks if name in BARS), None)
    if bar == "iqr":
        ax.add_patch(Rectangle((position - half, held(found["q1"])), 2 * half, held(found["q3"]) - held(found["q1"]),
                               facecolor=color, edgecolor="none", linewidth=0))
    elif bar and math.isfinite(found["sd"]):
        bottom, top = interval_of(found, bar)
        slim = half * tokens["summary"]["thin_bar"]
        ax.add_patch(Rectangle((position - slim, bottom), 2 * slim, top - bottom, facecolor=color, edgecolor="none",
                               linewidth=0))
    if "median" in marks:
        ax.plot([position - half, position + half], [held(found["median"])] * 2, linewidth=width,
                color=settings.neutral["surface"] if bar == "iqr" else color, solid_capstyle="butt",
                label="_nolegend_", gid=FIXED_ID)
    if "mean" in marks:
        size = DIAMOND * tokens["lines"]["point_radius"] * settings.base_size * math.sqrt(2)
        ax.plot([position], [held(found["mean"])], marker="D", markersize=size, linestyle="none",
                markerfacecolor=settings.neutral["surface"], markeredgecolor=color, markeredgewidth=width * OPEN_EDGE,
                label="_nolegend_", gid=FIXED_ID)


def draw_brackets(ax, comparisons: Sequence[tuple[str, str, str]], names: list[str], values: pd.Series,
                  rules: dict) -> int:
    """The brackets, each on the lowest level free of the others; returns the number of levels."""
    settings = current_settings()
    top, spread = float(values.max()), float(values.max() - values.min()) or 1.0
    spans = [(names.index(first), names.index(second)) for first, second, _ in comparisons]
    width, color = load_tokens()["reference"]["width"] * settings.base_size, settings.neutral["muted"]
    levels = bracket_levels(spans)
    for (low, high), level, (_, _, label) in zip(spans, levels, comparisons, strict=True):
        y = top + spread * rules["bracket_step"] * (level + 1)
        tick = spread * rules["bracket_tick"]
        ax.plot([low, low, high, high], [y - tick, y, y, y - tick], color=color, linewidth=width,
                label="_nolegend_", gid=FIXED_ID)
        ax.annotate(label, xy=((low + high) / 2, y), xytext=(0, rules["label_pad"] * role_size(settings, "label")),
                    textcoords="offset points", ha="center", va="bottom", fontsize=role_size(settings, "label"),
                    color=color, fontfamily=families(settings.font), annotation_clip=False)
        ax.update_datalim([(low, y + spread * rules["bracket_step"] * BRACKET_HEADROOM)])
    return max(levels, default=-1) + 1


def resolve_comparisons(comparisons: str | Sequence[tuple], groups: list, value: str) -> list[tuple[str, str, str]]:
    names = [name for name, _ in groups]
    if isinstance(comparisons, str):
        if comparisons not in ("all", "adjacent"):
            raise ValueError(f"hairline: raincloud: comparisons {comparisons!r} must be 'all', 'adjacent' or a list")
        pairs = [(names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names))
                 if comparisons == "all" or j == i + 1]
    else:
        pairs = list(comparisons)
    check_comparisons([(*pair[:2], "") for pair in pairs], names)
    values = dict(groups)
    return [tuple(pair) if len(pair) == 3 else (pair[0], pair[1], format_p(rank_sum(values[pair[0]][value],
                                                                                    values[pair[1]][value])))
            for pair in pairs]


def check_comparisons(comparisons: Sequence[tuple[str, str, str]], names: list[str]) -> None:
    for first, second, _ in comparisons:
        for name in (first, second):
            if name not in names:
                raise ValueError(f"hairline: raincloud: comparison group {name!r} is not one of: {', '.join(names)}")


def draw_panel(ax, drawn: list, counted: list, comparisons: str | Sequence[tuple], value: str,
               palette: dict, marks: Sequence[str] = DEFAULT_SUMMARY) -> int:
    """One panel's groups at their positions (a group without values here is left empty) and its comparisons,
    tested on this panel's values; returns the bracket levels."""
    rules, names = load_tokens()["raincloud"], [name for name, _ in drawn]
    present = [(name, rows) for name, rows in counted if len(rows)]
    for position, ((name, rows), (_, all_rows)) in enumerate(zip(drawn, counted, strict=True)):
        if len(rows):
            draw_group(ax, rows[value], position, palette[name], rules, all_rows[value], marks)
    pairs = resolve_comparisons(comparisons, present, value)
    check_comparisons(pairs, [name for name, _ in present])
    shown = pd.concat([rows[value] for _, rows in drawn if len(rows)])
    return draw_brackets(ax, pairs, names, shown, rules)


def check_raincloud_stats(stats: str | Sequence[str], facet: str | None) -> tuple[str, ...]:
    """The measures written under the groups; n has its own row (show_n), and panels have no row under them."""
    stats = as_names(stats, "raincloud", "stats", SUMMARY_NAMES)
    if stats and facet:
        raise ValueError("hairline: raincloud: stats writes a row of numbers under the groups, which facet panels do "
                         "not have; use spread(facet=...), which lists the numbers beside each block's rows")
    return stats


def stat_rows(groups: Sequence[pd.Series], stats: Sequence[str], percent: bool, locale: str) -> list[tuple]:
    """One table row per measure, its label on the left, each group's number under the group."""
    if not stats:
        return []
    values = [values.to_numpy(dtype=float) for values in groups]
    numbers = measure_numbers(np.concatenate(values), percent, None)
    found = [stat_pairs(group, stats, numbers, locale=locale) for group in values]
    return [(found[0][row][0], None, [(float(position), pairs[row][1]) for position, pairs in enumerate(found)])
            for row in range(len(stats))]


def raincloud(data: pd.DataFrame, group: str, value: str, *, title: str | None = None, subtitle: str | None = None,
              caption: str | None = None, y_title: str | None = None, order: Sequence[str] | None = None,
              comparisons: str | Sequence[tuple] = (), colors: Mapping[str, str] | None = None,
              size: str = "onehalf", min_n: int | None = None,
              clip: float | tuple[float | None, float | None] | None = None, clip_stats: bool = False,
              color_by: str | None = None, dimension: str | None = None, sort: str | None = None,
              percent: bool = False, show_n: bool = True, x_title: str | None = None, reference: Reference = None,
              highlight: Sequence[str] | str | None = None, key_title: str | None = None, facet: str | None = None,
              columns: int | None = None, summary: str | Sequence[str] | None = None,
              stats: str | Sequence[str] = ()) -> HairlineFigure:
    """Distributions per group. `comparisons`: "all" or "adjacent" pairs, (group, group) pairs, or
    (group, group, text) with your own result; pairs without a text get a Wilcoxon rank-sum p. Missing values are
    left out, and "n = …" counts the values the statistics use (`show_n=False` leaves it out). `min_n`, `clip`,
    `color_by` and `dimension` work as in `spread()`: groups too small and values clipped off are named in the
    caption. Shared with the other charts: `sort` ("median", "mean", "n"), `percent`, `x_title`, `reference`
    (lines on the value axis), `highlight` (groups kept in colour), `key_title` and `facet` (one panel per value,
    in `columns` columns, on a shared value axis; each panel's n in its header, its comparisons within it).

    `summary` chooses the marks at the box's place, from "median" (a tick), "mean" (an open diamond), "iqr" (the
    box), "range" (a thin line), "sd" and "ci" (the mean's SD or 95 % CI as a slim bar); one bar at most. The
    default is ("median", "iqr"); a summary you give is named in the legend. `stats` writes the same measures as
    rows of numbers under the groups ("median", "mean", "iqr", "range", "sd", "ci")."""
    check_columns(data, [group, value, color_by, facet])
    marks = DEFAULT_SUMMARY if summary is None else check_summary(summary, "raincloud")
    stats = check_raincloud_stats(stats, facet)
    check_present(data, value, "raincloud")
    data = data[data[value].notna()]
    check_numeric(data, [value], "raincloud")
    locale = current_settings().locale
    groups = groups_of(data, group, order, "raincloud")
    kept, small = drop_small([(name, rows[value].to_numpy(dtype=float)) for name, rows in groups], min_n,
                             "raincloud", locale)
    groups = sorted_groups([(name, rows) for name, rows in groups if name in dict(kept)], sort, "raincloud",
                           lambda rows: rows[value].to_numpy(dtype=float))
    every = data[value].to_numpy(dtype=float)
    limits = clip_limits(np.concatenate([values for _, values in kept]), clip, "raincloud")
    drawn = [(name, rows[rows[value].between(*limits)]) for name, rows in groups]
    counted = drawn if clip_stats else groups
    names = [name for name, _ in groups]
    title = title or f"{humanise(value)} by {str(group).replace('_', ' ')}"
    notes = [small, clip_caption(every, limits, clip_stats, locale) if clip is not None else None]
    panels = groups_of(data, facet, None, "raincloud") if facet else [(None, data)]
    result = figure(title, subtitle=subtitle, caption=with_caption(caption, *notes), size=size, panels=len(panels),
                    layout="grid" if facet else "rows", columns=columns or (min(len(panels), 2) if facet else 1),
                    sharey=bool(facet))
    palette, coarse = series_colors(names, data, group, color_by, colors, dimension, "raincloud", highlight,
                                    named=True)
    levels = 0
    for index, (panel, _) in enumerate(panels):
        def in_panel(rows: pd.DataFrame, panel: str | None = panel) -> pd.DataFrame:
            return rows if panel is None else rows[rows[facet].astype(str) == panel]
        drawn_here = [(name, in_panel(rows)) for name, rows in drawn]
        counted_here = [(name, in_panel(rows)) for name, rows in counted]
        levels = max(levels, draw_panel(result.axes[index], drawn_here, counted_here, comparisons, value, palette,
                                        marks))
        result.categories(index, names)
        result.axes[index].set_xlim(-0.6, len(names) - 0.4)
        if panel is not None:
            total = sum(len(rows) for _, rows in counted_here)
            result.panel_header(index, panel, stats=[("n", format_number(total, 0, locale))] if show_n else None)
        if percent:
            result.percent_axis(index, "y")
    # A short plot (one column of a two-column page) would stack the p labels into the brackets above them.
    result.min_plot = bracket_plot_height(levels)
    counts = [format_number(len(rows), 0, locale) for _, rows in counted]
    table = [("", None, [(float(position), word("n_equals", locale, n=count)) for position, count in
                         enumerate(counts)])] if show_n and not facet else []
    # Where "n = 20" under each group would meet, the row reads "n" and then the bare counts.
    compact = [("n", list(enumerate(counts)))] if table else []
    table += stat_rows([rows[value] for _, rows in counted], stats, percent, locale)
    if table:
        result.table(table, compact=compact)
    legend = [("square", color, label) for label, color in
              dict.fromkeys((coarse[name], palette[name]) for name in names)] if color_by else []
    legend += summary_legend(marks, "line", current_settings().neutral["ink"], locale) if summary is not None else []
    if legend:
        result.legend(legend)
    return apply_options(result, "raincloud", names=names, x_title=x_title, y_title=y_title, reference=reference,
                         key_title=key_title)
