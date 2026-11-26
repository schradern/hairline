"""One value over a grid of two numeric axes, shared by the surface and the heatmap: reading the grid from a data
frame, the colour scale (bands or a gradient) with its key, and the texts a pointer reads. Mirrored in R's
grid_values.R."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from hairline.charts.common import check_columns, check_numeric, check_present
from hairline.charts.time_of_day import step_index
from hairline.numbers import auto_digits, format_number, format_percent, snap_noise
from hairline.palettes import default_ramp, ramp, ramp_kind
from hairline.ticks import nice_breaks
from hairline.tokens import load_tokens


def value_texts(values, percent: bool, locale: str) -> list[str]:
    """Values with the shared digits rule (percentages for shares), in the figure's locale."""
    array = np.asarray(values, dtype=float)
    if percent:
        digits = auto_digits(array * 100)
        return [format_percent(snap_noise(value), digits, locale) for value in array]
    digits = auto_digits(array)
    return [format_number(snap_noise(value), digits, locale) for value in array]


def read_grid(data: pd.DataFrame, x: str, y: str, z: str, chart: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The distinct x and y values in order and z on their grid (rows y, columns x); a pair without a row is missing."""
    check_columns(data, [x, y, z])
    check_numeric(data, [x, y, z], chart)
    for column in (x, y):
        check_present(data, column, chart)
    rows = data[[x, y, z]].dropna(subset=[x, y])
    repeated = rows[rows.duplicated([x, y], keep=False)]
    if len(repeated):
        first = repeated.iloc[0]
        raise ValueError(f"hairline: {chart}: {len(repeated)} rows share an ({x}, {y}) pair, such as "
                         f"({first[x]:g}, {first[y]:g}); give one '{z}' per pair (aggregate first)")
    xs, ys = np.sort(rows[x].unique()).astype(float), np.sort(rows[y].unique()).astype(float)
    most = load_tokens()["surface"]["max_side"]
    for column, values in ((x, xs), (y, ys)):
        if not 2 <= len(values) <= most:
            raise ValueError(f"hairline: {chart}: '{column}' needs 2 to {most} distinct values for a grid; got "
                             f"{len(values)}" + ("; bin it first" if len(values) > most else ""))
    grid = rows.pivot(index=y, columns=x, values=z).reindex(index=ys, columns=xs).to_numpy(dtype=float)
    if not np.isfinite(grid).any():
        raise ValueError(f"hairline: {chart}: '{z}' is missing in every row; there is nothing to colour")
    return xs, ys, grid


def step_colors(colors: str | None, count: int) -> list[str]:
    """A colour per step: a sequential ramp without its lightest colour (which would vanish on the page), a
    diverging ramp from pole to pole."""
    name = colors or default_ramp("sequential")
    return ramp(name, count) if ramp_kind(name) == "diverging" else ramp(name, count + 1)[1:]


def color_steps(breaks: list[float], high: float) -> list[float]:
    """The upper edges of the colour bins, from the first tick up past the highest value: half a tick step each, so
    the bands read as contours, while that keeps the key to `max_bins` squares (it shares one legend row); a whole
    tick step each otherwise."""
    for share in (0.5, 1.0):
        width = (breaks[1] - breaks[0]) * share
        count = max(1, math.ceil((high - breaks[0]) / width - 1e-9))
        if count <= load_tokens()["surface"]["max_bins"] or share == 1.0:
            return [float(f"{breaks[0] + index * width:.10g}") for index in range(1, count + 1)]
    raise AssertionError("unreachable: the whole step always returns")


def ramp_position(value: float, limits: tuple[float, float], count: int) -> int:
    """The colour of `value` among `count` blended along the axis from its low to its high limit."""
    share = (value - limits[0]) / (limits[1] - limits[0])
    return min(count - 1, max(0, int(math.floor(share * (count - 1) + 0.5))))


def color_scale(grid: np.ndarray, breaks: list[float], colors: str | None, gradient: bool) -> dict:
    """How values become colours, and the key in the legend row: bands of `color_steps()` by default; with
    `gradient`, a blend along the ramp keyed at each tick (every other tick past `max_bins`, to keep one row)."""
    low, high = float(np.nanmin(grid)), float(np.nanmax(grid))
    rules = load_tokens()["surface"]
    if gradient:
        limits = (min(low, breaks[0]), max(high, breaks[-1]))
        blend = step_colors(colors, rules["gradient_steps"])
        steps = breaks if len(breaks) <= rules["max_bins"] else breaks[::2]
        key = [blend[ramp_position(step, limits, len(blend))] for step in steps]
        return {"blend": blend, "limits": limits,
                "key": {"colors": key, "steps": list(steps), "limits": list(limits)}}
    steps = color_steps(breaks, high)
    colours = step_colors(colors, len(steps))
    limits = (min(low, breaks[0]), max(high, breaks[-1], steps[-1]))
    return {"colors": colours, "steps": steps, "key": {"colors": colours, "steps": steps, "limits": list(limits)}}


def fills(values: np.ndarray, scale: dict) -> list[list[str | None]]:
    """The colour of each value on the scale; None where it is missing."""
    def colour(value: float) -> str:
        if "blend" in scale:
            return scale["blend"][ramp_position(value, scale["limits"], len(scale["blend"]))]
        return scale["colors"][step_index(value, scale["steps"])]
    return [[colour(float(value)) if np.isfinite(value) else None for value in row] for row in values]


def corner_means(grid: np.ndarray) -> np.ndarray:
    """Each cell between four grid points: the mean of its corners, missing where one is."""
    return np.stack([grid[:-1, :-1], grid[:-1, 1:], grid[1:, 1:], grid[1:, :-1]]).mean(axis=0)


def grid_tips(xs: np.ndarray, ys: np.ndarray, grid: np.ndarray, percent: bool, locale: str) -> dict:
    """What a pointer reads at each grid point: its x, its y and its value."""
    known = grid[np.isfinite(grid)]
    digits = auto_digits(known * 100 if percent else known)
    write = (lambda value: format_percent(snap_noise(value), digits, locale)) if percent else \
        (lambda value: format_number(snap_noise(value), digits, locale))
    return {"x": value_texts(xs, False, locale), "y": value_texts(ys, False, locale),
            "z": [[write(value) if np.isfinite(value) else "" for value in row] for row in grid]}


def inner_ticks(low: float, high: float, locale: str, place) -> list[dict]:
    """Round values within low to high, each placed by `place(value)`."""
    target = load_tokens()["surface"]["ticks"]
    inside = [tick for tick in nice_breaks(low, high, target) if low - 1e-9 <= tick <= high + 1e-9]
    return [{"at": place(tick), "text": text} for tick, text in zip(inside, value_texts(inside, False, locale),
                                                                       strict=True)]
