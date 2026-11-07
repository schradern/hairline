"""Raincloud: per group a half density, the box (IQR and median) and the points, with
"n = …" under the group names and comparison brackets stacked without overlap."""

from __future__ import annotations

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
from hairline.charts.timeseries import groups_of
from hairline.figure import HairlineFigure, figure
from hairline.fonts import families
from hairline.layout.geometry import load_font_metrics
from hairline.marks import FIXED_ID, STATIC_ID
from hairline.numbers import format_number, format_p, word
from hairline.settings import current_settings, role_size
from hairline.stats.density import density, jitter_offsets, quantiles
from hairline.stats.tests import rank_sum
from hairline.tokens import load_tokens

DENSITY_ID = "hairline-density"
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


def draw_group(ax, values: pd.Series, position: int, color: str, rules: dict,
               counted: pd.Series | None = None) -> None:
    """Density and points of the values drawn; the box (interquartile range, median) of the values counted, held
    within the drawn range."""
    settings = current_settings()
    surface, width = settings.neutral["surface"], load_tokens()["lines"]["data"] * settings.base_size
    counted = values if counted is None else counted
    curve = density(values)
    if curve is not None:
        grid, height = curve
        peak, start = max(height), position + rules["density_offset"]
        outline = [(start + value / peak * rules["density_width"], level) for level, value in zip(grid, height,
                                                                                                    strict=True)]
        ax.add_patch(Polygon([(start, grid[0])] + outline + [(start, grid[-1])], closed=True, facecolor=color,
                             alpha=rules["density_opacity"], edgecolor="none", linewidth=0, gid=DENSITY_ID))
    low, middle, high = (min(max(value, float(values.min())), float(values.max()))
                         for value in quantiles(counted, [0.25, 0.5, 0.75]))
    half = rules["box_half"]
    ax.add_patch(Rectangle((position - half, low), 2 * half, high - low, facecolor=color, edgecolor="none",
                           linewidth=0))
    ax.plot([position - half, position + half], [middle, middle], color=surface, linewidth=width,
            solid_capstyle="butt", label="_nolegend_", gid=FIXED_ID)
    xs = [position + rules["points_centre"] + offset * rules["points_spread"] for offset in jitter_offsets(len(values))]
    ax.scatter(xs, values, color=color, label="_nolegend_", gid=STATIC_ID)


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


def raincloud(data: pd.DataFrame, group: str, value: str, *, title: str | None = None, subtitle: str | None = None,
              caption: str | None = None, y_title: str | None = None, order: Sequence[str] | None = None,
              comparisons: str | Sequence[tuple] = (), colors: Mapping[str, str] | None = None,
              size: str = "onehalf", min_n: int | None = None,
              clip: float | tuple[float | None, float | None] | None = None, clip_stats: bool = False,
              color_by: str | None = None, dimension: str | None = None, sort: str | None = None,
              percent: bool = False, show_n: bool = True, x_title: str | None = None, reference: Reference = None,
              highlight: Sequence[str] | str | None = None, key_title: str | None = None) -> HairlineFigure:
    """Distributions per group. `comparisons`: "all" or "adjacent" pairs, (group, group) pairs, or
    (group, group, text) with your own result; pairs without a text get a Wilcoxon rank-sum p. Missing values are
    left out, and "n = …" counts the values the statistics use (`show_n=False` leaves it out). `min_n`, `clip`,
    `color_by` and `dimension` work as in `spread()`: groups too small and values clipped off are named in the
    caption. Shared with the other charts: `sort` ("median", "mean", "n"), `percent`, `x_title`, `reference`
    (lines on the value axis), `highlight` (groups kept in colour) and `key_title`."""
    check_columns(data, [group, value, color_by])
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
    comparisons = resolve_comparisons(comparisons, counted, value)
    check_comparisons(comparisons, names)
    notes = [small, clip_caption(every, limits, clip_stats, locale) if clip is not None else None]
    rules = load_tokens()["raincloud"]
    result = figure(title, subtitle=subtitle, caption=with_caption(caption, *notes), size=size)
    palette, coarse = series_colors(names, data, group, color_by, colors, dimension, "raincloud", highlight)
    for position, ((name, rows), (_, all_rows)) in enumerate(zip(drawn, counted, strict=True)):
        draw_group(result.ax, rows[value], position, palette[name], rules, all_rows[value])
    shown = pd.concat([rows[value] for _, rows in drawn])
    # A short plot (one column of a two-column page) would stack the p labels into the brackets above them.
    result.min_plot = bracket_plot_height(draw_brackets(result.ax, comparisons, names, shown, rules))
    result.categories(0, names)
    result.ax.set_xlim(-0.6, len(names) - 0.4)
    if show_n:
        result.table([("", None, [(float(position), word("n_equals", locale, n=format_number(len(rows), 0, locale)))
                                  for position, (_, rows) in enumerate(counted)])])
    if percent:
        result.percent_axis(0, "y")
    if color_by:
        result.legend([("square", color, label) for label, color in
                       dict.fromkeys((coarse[name], palette[name]) for name in names)])
    return apply_options(result, "raincloud", names=names, x_title=x_title, y_title=y_title, reference=reference,
                         key_title=key_title)
