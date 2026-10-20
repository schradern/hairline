"""Scatter with fit: points, a linear fit with its 95 % band in ink, n, r and slope as key
numbers."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from hairline import entities
from hairline.charts.common import check_columns, humanise
from hairline.charts.timeseries import groups_of
from hairline.figure import HairlineFigure, figure
from hairline.marks import STATIC_ID, lone_color
from hairline.numbers import format_number
from hairline.settings import current_settings
from hairline.stats.tests import fit_band, linear_fit, pearson
from hairline.tokens import load_tokens


def fit_stats(x: pd.Series, y: pd.Series, locale: str) -> list[tuple[str, str]]:
    r, _ = pearson(x, y)
    slope = linear_fit(x, y)["slope"]
    return [("n", format_number(len(x), 0, locale)), ("r", format_number(r, 2, locale)),
            ("Slope", format_number(slope, 2, locale))]


def check_fit(x: pd.Series) -> None:
    """A line and its band need three points and two x values; fewer leave slope or band undefined."""
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
            order: list[str] | None = None, colors: Mapping[str, str] | None = None,
            size: str = "onehalf") -> HairlineFigure:
    """Points per group (entity colours) and, with `fit="linear"`, a fit over all points with n, r and slope."""
    check_columns(data, [x, y, by])
    if fit not in ("linear", None):
        raise ValueError(f"hairline: scatter: fit {fit!r} must be 'linear' or None")
    rows = data.dropna(subset=[x, y])
    result = figure(title or f"{humanise(y)} and {str(x).replace('_', ' ')}", subtitle=subtitle, caption=caption,
                    size=size)
    groups = groups_of(rows, by, order)
    with entities.chart([name for name, _ in groups] if by else [], colors):
        for name, group in groups:
            color = entities.color(name) if by else lone_color()
            result.ax.scatter(group[x], group[y], color=color, label=name if by else "_nolegend_")
    if fit:
        check_fit(rows[x])
        draw_fit(result.ax, rows[x], rows[y])
        result.panel_header(0, "Linear fit", stats=fit_stats(rows[x], rows[y], current_settings().locale))
    result.y_title(humanise(y))
    result.x_title(humanise(x))
    if by:
        result.legend()
    return result
