"""Scatter with fit: points, a linear fit with its 95 % band in ink, n, r and slope as key
numbers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from hairline.charts.common import (
    check_columns,
    check_finite,
    check_numeric,
    clip_caption,
    clip_limits,
    humanise,
    series_colors,
    with_caption,
    without_small_categories,
)
from hairline.charts.options import Reference, apply_options
from hairline.charts.timeseries import groups_of
from hairline.figure import HairlineFigure, figure
from hairline.marks import STATIC_ID, lone_color
from hairline.numbers import format_number, significant_places
from hairline.settings import current_settings
from hairline.stats.tests import fit_band, linear_fit, pearson
from hairline.tokens import load_tokens


def fit_stats(x: pd.Series, y: pd.Series, locale: str) -> list[tuple[str, str]]:
    r, _ = pearson(x, y)
    slope = linear_fit(x, y)["slope"]
    return [("n", format_number(len(x), 0, locale)), ("r", format_number(r, 2, locale)),
            ("Slope", format_number(slope, significant_places(slope), locale))]


def check_fit(x: pd.Series) -> None:
    """A line and its band need numbers on x, three points and two x values; fewer leave slope or band
    undefined."""
    if not pd.api.types.is_numeric_dtype(x) or pd.api.types.is_bool_dtype(x):
        raise ValueError(f"hairline: scatter: a linear fit needs numbers on x; got {x.dtype}; use fit=None for the "
                         f"points alone")
    distinct = x.nunique()
    if len(x) < 3 or distinct < 2:
        raise ValueError(f"hairline: scatter: a linear fit needs at least 3 points with x and y and 2 different x "
                         f"values; got {len(x)} point(s) and {distinct} x value(s); use fit=None for the points alone")


def draw_fit(ax, x: pd.Series, y: pd.Series) -> None:
    settings, rules = current_settings(), load_tokens()["fit"]
    xs = np.linspace(float(x.min()), float(x.max()), rules["points"])
    centre, low, high = fit_band(linear_fit(x, y), xs)
    ink = settings.neutral["ink"]
    ax.fill_between(xs, low, high, color=ink, alpha=rules["band_opacity"], linewidth=0, label="_nolegend_")
    ax.plot(xs, centre, color=ink, linewidth=load_tokens()["lines"]["data"] * settings.base_size, label="_nolegend_",
            gid=STATIC_ID)


def scatter(data: pd.DataFrame, x: str, y: str, by: str | None = None, *, title: str | None = None,
            subtitle: str | None = None, caption: str | None = None, fit: str | None = "linear",
            order: list[str] | None = None, colors: Mapping[str, str] | None = None, size: str = "onehalf",
            clip: float | tuple[float | None, float | None] | None = None, clip_stats: bool = False,
            color_by: str | None = None, dimension: str | None = None, min_n: int | None = None,
            percent: bool = False, x_title: str | None = None, y_title: str | None = None,
            reference: Reference = None, highlight: Sequence[str] | str | None = None,
            key_title: str | None = None, facet: str | None = None, columns: int | None = None) -> HairlineFigure:
    """Points per group (entity colours) and, with `fit="linear"`, a fit over all points drawn (the groups in
    `order`, when given) with n, r and slope. `clip` hides implausible y values (as in `spread()`) and says so in
    the caption; the fit still uses every point unless `clip_stats`. `color_by` colours the groups of `by` by a
    coarser column, which the legend lists; `dimension` keeps them off another dimension's slots. Shared with the
    other charts: `min_n` (groups of `by` with fewer points are left out and named), `percent` (the y axis),
    `x_title`, `y_title`, `reference` (lines at y values), `highlight` (groups kept in colour), `key_title` and
    `facet` (one panel per value, in `columns` columns, on shared axes, each with its own fit)."""
    check_columns(data, [x, y, by, color_by, facet])
    check_numeric(data, [y], "scatter")
    check_finite(data, x, "scatter")
    if fit not in ("linear", None):
        raise ValueError(f"hairline: scatter: fit {fit!r} must be 'linear' or None")
    if color_by is not None and by is None:
        raise ValueError("hairline: scatter: color_by needs by=, the groups it colours")
    rows = data.dropna(subset=[x, y])
    if not len(rows):
        raise ValueError(f"hairline: scatter: no rows with both '{x}' and '{y}' to draw")
    rows, small = without_small_categories(rows, by, min_n, "scatter") if by else (rows, None)
    locale = current_settings().locale
    groups = groups_of(rows, by, order, "scatter")
    every = pd.concat([group for _, group in groups])[y].to_numpy(dtype=float)
    limits = clip_limits(every, clip, "scatter")
    note = clip_caption(every, limits, clip_stats, locale) if clip is not None else None
    rows = pd.concat([group for _, group in groups])
    panels = groups_of(rows, facet, None, "scatter") if facet else [(None, rows)]
    result = figure(title or f"{humanise(y)} and {str(x).replace('_', ' ')}", subtitle=subtitle,
                    caption=with_caption(caption, note, small), size=size, panels=len(panels),
                    layout="grid" if facet else "rows", columns=columns or (min(len(panels), 2) if facet else 1),
                    sharex=bool(facet), sharey=bool(facet))
    names = [name for name, _ in groups]
    palette, coarse = series_colors(names, rows, by, color_by, colors, dimension, "scatter",
                                    highlight) if by else ({}, {})
    for index, (panel, panel_rows) in enumerate(panels):
        draw_points(result.axes[index], panel_rows, x, y, by, names, palette, coarse, limits)
        if fit:
            drawn = panel_rows[panel_rows[y].between(*limits)] if clip_stats else panel_rows
            check_fit(drawn[x])
            draw_fit(result.axes[index], drawn[x], drawn[y])
            result.panel_header(index, "Linear fit" if panel is None else panel,
                                stats=fit_stats(drawn[x], drawn[y], locale))
        elif panel is not None:
            result.panel_header(index, panel)
        if percent:
            result.percent_axis(index, "y")
    if by:
        result.legend()
    return apply_options(result, "scatter", names=names, x_title=x_title or humanise(x),
                         y_title=y_title or humanise(y), reference=reference, key_title=key_title)


def draw_points(ax, rows: pd.DataFrame, x: str, y: str, by: str | None, names: list[str], palette: dict,
                coarse: dict, limits: tuple[float, float]) -> None:
    """One panel's points, a group at a time in its colour, those outside the clip limits left out."""
    for name in names:
        group = rows[rows[by].astype(str) == name] if by else rows
        shown = group[group[y].between(*limits)]
        # Limits end on a break, so a point at the limit would be cut in half by the panel's edge.
        ax.scatter(shown[x], shown[y], color=palette[name] if by else lone_color(),
                   label=coarse[name] if by else "_nolegend_", clip_on=False)
