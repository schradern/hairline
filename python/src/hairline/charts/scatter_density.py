"""Scatter density: the points counted in a grid of hexagons, each coloured by its count in the bins of a ramp and
keyed in the legend row, for clouds too dense to read point by point. Pointy-top hexagons, `bins` across the x
range and as many rows as keep them regular on the plot they fill: `density.aspect` as tall as it is wide alone
(a scatter's plot after its title, legend, header and axis texts), a grid of panels times its columns over its rows.
The size is known only when a figure is saved, so this is the one shape both packages assume. Pure numbers;
mirrored in R's scatter_density.R."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from hairline.alt_text import TIE_DIGITS
from hairline.charts.grid_values import step_colors
from hairline.charts.time_of_day import step_index
from hairline.numbers import format_number, word
from hairline.ticks import nice_breaks
from hairline.tokens import load_tokens

ROOT3 = math.sqrt(3)


def density_bins(density: bool | int, chart: str) -> int | None:
    """Hexagons across the x range: the token's with `density=True`, the number given, or None for points."""
    if density is False or density is None:
        return None
    rules = load_tokens()["density"]
    if density is True:
        return int(rules["bins"])
    if isinstance(density, bool) or not isinstance(density, (int, np.integer)) or density < rules["min_bins"]:
        raise ValueError(f"hairline: {chart}: density must be True, False or a whole number of hexagons across of at "
                         f"least {rules['min_bins']}; got {density!r}")
    return int(density)


def hex_grid(x: np.ndarray, y: np.ndarray, bins: int, chart: str, shape: tuple[int, int] = (1, 1)) -> dict:
    """The lattice over every point drawn: its origin (the lowest x and y), the spacing of hexagon centres in a row
    and between rows, in data units; `shape` the panels' (columns, rows)."""
    x_range, y_range = float(np.max(x) - np.min(x)), float(np.max(y) - np.min(y))
    if not (x_range > 0 and y_range > 0):
        raise ValueError(f"hairline: {chart}: density needs points spread along both axes; got an x range of "
                         f"{x_range:g} and a y range of {y_range:g}; use density=False for the points alone")
    aspect = load_tokens()["density"]["aspect"] * shape[0] / shape[1]
    return {"x0": float(np.min(x)), "y0": float(np.min(y)), "width": x_range / bins,
            "height": ROOT3 / 2 * y_range / (bins * aspect)}


def nearest_cells(x: np.ndarray, y: np.ndarray, grid: dict) -> tuple[np.ndarray, np.ndarray]:
    """Each point's hexagon as (row, column): the nearer of the centres on the even and the odd rows, measured on
    the regular lattice; a point as near to both takes the even row."""
    across = (np.asarray(x, dtype=float) - grid["x0"]) / grid["width"]
    up = (np.asarray(y, dtype=float) - grid["y0"]) / grid["height"]
    even_row, even_column = 2 * np.floor(up / 2 + 0.5), np.floor(across + 0.5)
    odd_row, odd_column = 2 * np.floor((up - 1) / 2 + 0.5) + 1, np.floor(across)
    even = np.round((across - even_column) ** 2 + ((up - even_row) * ROOT3 / 2) ** 2, TIE_DIGITS)
    odd = np.round((across - odd_column - 0.5) ** 2 + ((up - odd_row) * ROOT3 / 2) ** 2, TIE_DIGITS)
    nearer = even <= odd
    return np.where(nearer, even_row, odd_row).astype(int), np.where(nearer, even_column, odd_column).astype(int)


def hex_counts(x: np.ndarray, y: np.ndarray, grid: dict) -> list[dict]:
    """The hexagons with points, bottom row first and left to right: row, column, centre and count."""
    rows, columns = nearest_cells(x, y, grid)
    counted: dict[tuple[int, int], int] = {}
    for cell in zip(rows.tolist(), columns.tolist(), strict=True):
        counted[cell] = counted.get(cell, 0) + 1
    return [{"row": row, "column": column, "count": count,
             "x": grid["x0"] + (column + (row % 2) / 2) * grid["width"], "y": grid["y0"] + row * grid["height"]}
            for (row, column), count in sorted(counted.items())]


def hex_corners(cell: dict, grid: dict) -> list[list[float]]:
    """A hexagon's six corners from the top, clockwise."""
    half, third = grid["width"] / 2, grid["height"] / 3
    offsets = [(0, 2 * third), (half, third), (half, -third), (0, -2 * third), (-half, -third), (-half, third)]
    return [[cell["x"] + across, cell["y"] + up] for across, up in offsets]


def count_steps(top: int) -> list[float]:
    """The upper edges of the colour bins for counts up to `top`: whole round steps from the first past zero up to
    `top` or beyond, at most `density.max_bins` of them."""
    most = load_tokens()["density"]["max_bins"]
    breaks = nice_breaks(0.0, float(top), load_tokens()["surface"]["ticks"], whole=True)
    step = max(1.0, breaks[1] - breaks[0])
    while math.ceil(top / step - 1e-9) > most:
        step *= 2
    return [step * index for index in range(1, math.ceil(top / step - 1e-9) + 1)]


def density_scale(counts: Sequence[int], colors: str | None) -> dict:
    """The bins of the counts, a colour for each from the ramp `colors`, and the legend row's key."""
    steps = count_steps(max(counts))
    colours = step_colors(colors, len(steps))
    return {"steps": steps, "colors": colours, "key": {"colors": colours, "steps": steps, "limits": [0.0, steps[-1]]}}


def count_text(count: int, locale: str) -> str:
    """'1 point', '12 points': what a hexagon's tooltip reads."""
    return word("hexagon_one", locale) if count == 1 else \
        word("hexagon_many", locale, n=format_number(count, 0, locale))


def hex_fill(count: int, scale: dict) -> str:
    return scale["colors"][step_index(count, scale["steps"])]
