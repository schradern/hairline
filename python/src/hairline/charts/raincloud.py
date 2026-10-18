"""Raincloud: per group a half density, the box (IQR and median) and the points, with
"n = …" under the group names and comparison brackets stacked without overlap."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd
from matplotlib.patches import Polygon, Rectangle

from hairline import entities
from hairline.charts.common import check_columns, humanise
from hairline.charts.timeseries import groups_of
from hairline.figure import HairlineFigure, figure
from hairline.marks import FIXED_ID, STATIC_ID
from hairline.numbers import format_p
from hairline.settings import current_settings, role_size
from hairline.stats.density import density, jitter_offsets, quantiles
from hairline.stats.tests import rank_sum
from hairline.tokens import load_tokens

DENSITY_ID = "hairline-density"


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


def draw_group(ax, values: pd.Series, position: int, color: str, rules: dict) -> None:
    settings = current_settings()
    surface, width = settings.neutral["surface"], load_tokens()["lines"]["data"] * settings.base_size
    curve = density(values)
    if curve is not None:
        grid, height = curve
        peak, start = max(height), position + rules["density_offset"]
        outline = [(start + value / peak * rules["density_width"], level) for level, value in zip(grid, height,
                                                                                                    strict=True)]
        ax.add_patch(Polygon([(start, grid[0])] + outline + [(start, grid[-1])], closed=True, facecolor=color,
                             alpha=rules["density_opacity"], edgecolor="none", linewidth=0, gid=DENSITY_ID))
    low, middle, high = quantiles(values, [0.25, 0.5, 0.75])
    half = rules["box_half"]
    ax.add_patch(Rectangle((position - half, low), 2 * half, high - low, facecolor=color, edgecolor="none",
                           linewidth=0))
    ax.plot([position - half, position + half], [middle, middle], color=surface, linewidth=width,
            solid_capstyle="butt", label="_nolegend_", gid=FIXED_ID)
    xs = [position + rules["points_centre"] + offset * rules["points_spread"] for offset in jitter_offsets(len(values))]
    ax.scatter(xs, values, color=color, label="_nolegend_", gid=STATIC_ID)


def draw_brackets(ax, comparisons: Sequence[tuple[str, str, str]], names: list[str], values: pd.Series,
                  rules: dict) -> None:
    settings = current_settings()
    top, spread = float(values.max()), float(values.max() - values.min()) or 1.0
    spans = [(names.index(first), names.index(second)) for first, second, _ in comparisons]
    width, color = load_tokens()["reference"]["width"] * settings.base_size, settings.neutral["muted"]
    for (low, high), level, (_, _, label) in zip(spans, bracket_levels(spans), comparisons, strict=True):
        y = top + spread * rules["bracket_step"] * (level + 1)
        tick = spread * rules["bracket_tick"]
        ax.plot([low, low, high, high], [y - tick, y, y, y - tick], color=color, linewidth=width,
                label="_nolegend_", gid=FIXED_ID)
        ax.annotate(label, xy=((low + high) / 2, y), xytext=(0, rules["label_pad"] * role_size(settings, "label")),
                    textcoords="offset points", ha="center", va="bottom", fontsize=role_size(settings, "label"),
                    color=color, fontfamily=settings.font, annotation_clip=False)
        ax.update_datalim([(low, y + spread * rules["bracket_step"] * 0.6)])


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
              size: str = "onehalf") -> HairlineFigure:
    """Distributions per group. `comparisons`: "all" or "adjacent" pairs, (group, group) pairs, or
    (group, group, text) with your own result; pairs without a text get a Wilcoxon rank-sum p."""
    check_columns(data, [group, value])
    groups = groups_of(data, group, order)
    names = [name for name, _ in groups]
    title = title or f"{humanise(value)} by {str(group).replace('_', ' ')}"
    comparisons = resolve_comparisons(comparisons, groups, value)
    check_comparisons(comparisons, names)
    rules, result = load_tokens()["raincloud"], figure(title, subtitle=subtitle, caption=caption, size=size)
    with entities.chart(names, colors):
        for position, (name, rows) in enumerate(groups):
            draw_group(result.ax, rows[value], position, entities.color(name), rules)
    draw_brackets(result.ax, comparisons, names, data[value], rules)
    result.categories(0, names)
    result.ax.set_xlim(-0.6, len(names) - 0.4)
    if y_title:
        result.y_title(y_title)
    result.table([("", None, [(float(position), f"n = {len(rows)}") for position, (_, rows) in enumerate(groups)])])
    return result
