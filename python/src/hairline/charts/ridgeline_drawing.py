"""Ridgeline drawing on matplotlib axes: each ridge's fill and outline, its median line and mean diamond, spikes for
a group without a density, and what each draws in data units for its tooltip targets."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
from matplotlib.patches import Polygon

from hairline.charts.spread_geometry import DIAMOND, OPEN_EDGE
from hairline.charts.summaries import summary_values
from hairline.marks import STATIC_ID
from hairline.settings import current_settings
from hairline.tokens import load_tokens

RIDGE_ID, MEDIAN_ID = "hairline-ridge", "hairline-median"
# The most a plot grows (x its least height) to keep the bottom ridge's mean diamond inside it; a diamond lower still
# is lifted to the height that growth holds.
MEAN_GROWTH = 2


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


def diamond_reach() -> float:
    """How far the mean diamond reaches from its centre, in base sizes: its half-diagonal and half its outline."""
    lines = load_tokens()["lines"]
    return DIAMOND * lines["point_radius"] + lines["data"] * OPEN_EDGE / 2


def mean_floor(top: float) -> float:
    """The least height, in rows, of a bottom-row mean diamond above its baseline: where a plot grown MEAN_GROWTH
    times its least height (`top` rows high) just holds it."""
    return diamond_reach() * top / (MEAN_GROWTH * load_tokens()["spacing"]["min_plot_height"])


def mean_plot_height(lifts: list[float], top: float, panel_rows: int) -> float | None:
    """The least plot height (x the base size) at which each bottom-row mean diamond, `lifts` rows above its
    baseline, stays inside its panel (`top` rows high), for `panel_rows` rows of panels; None without one."""
    if not lifts:
        return None
    least = load_tokens()["spacing"]["min_plot_height"]
    return max(least, diamond_reach() * top / min(lifts) * panel_rows)


def draw_centres(ax, values: np.ndarray, curve: tuple[list[float], list[float]], base: float, scale: float,
                 layer: float, marks: Sequence[str], color: str,
                 floor: float = 0.0) -> tuple[list[dict], tuple[float, float] | None]:
    """The median as a line from the baseline up to the ridge, the mean as an open diamond on the ridge's outline
    (at least `floor` rows above the baseline); both held within the ridge. Returns them in data units, for the
    tooltip targets, and the median's top."""
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
        centre = (centre[0], max(centre[1], base + floor))
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
                statistics: list, floor: float = 0.0) -> dict[str, dict]:
    """Top row first, so each lower ridge is drawn in front of the one above; the bottom ridge's mean diamond at
    least `floor` rows above its baseline. Returns each ridge drawn: its marks in data units and where its tooltip
    points."""
    drawn = {}
    for index, ((name, values), curve, (_, counted)) in enumerate(zip(groups, curves, statistics, strict=True)):
        base, layer = float(len(groups) - 1 - index), 1 + index * 0.01
        top = None
        if curve is None:
            shapes = draw_spikes(ax, values, base, palette[name], layer)
        else:
            shapes = draw_ridge(ax, curve, base, scale, palette[name], layer)
            if len(counted):
                centres, top = draw_centres(ax, counted, curve, base, scale, layer, marks, palette[name],
                                            floor if base == 0 else 0.0)
                shapes += centres
        if shapes:
            drawn[name] = {"marks": shapes, "at": ridge_anchor(shapes, top)}
    return drawn
