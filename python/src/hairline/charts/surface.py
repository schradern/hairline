"""Surface: one value over two numeric axes (time of day by week, dose by age), drawn as a turned 3D surface from a
fixed viewpoint, its height binned into the steps of a ramp and keyed in the legend row. It shows the shape at once;
exact values are read from a 2D chart beside it, and the HTML export lets the reader turn it."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from hairline.charts.common import check_columns, check_numeric, check_present, humanise
from hairline.charts.surface_geometry import scene_shapes, surface_scene
from hairline.charts.time_of_day import step_index
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.numbers import auto_digits, format_number, format_percent, snap_noise
from hairline.palettes import default_ramp, ramp, ramp_kind
from hairline.settings import current_settings
from hairline.ticks import nice_breaks
from hairline.tokens import load_tokens

CHART = "surface"


def value_texts(values, percent: bool, locale: str) -> list[str]:
    """Values with the shared digits rule (percentages for shares), in the figure's locale."""
    array = np.asarray(values, dtype=float)
    if percent:
        digits = auto_digits(array * 100)
        return [format_percent(snap_noise(value), digits, locale) for value in array]
    digits = auto_digits(array)
    return [format_number(snap_noise(value), digits, locale) for value in array]


def surface_grid(data: pd.DataFrame, x: str, y: str, z: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The distinct x and y values in order and z on their grid (rows y, columns x); a pair without a row is missing."""
    check_columns(data, [x, y, z])
    check_numeric(data, [x, y, z], CHART)
    for column in (x, y):
        check_present(data, column, CHART)
    rows = data[[x, y, z]].dropna(subset=[x, y])
    repeated = rows[rows.duplicated([x, y], keep=False)]
    if len(repeated):
        first = repeated.iloc[0]
        raise ValueError(f"hairline: {CHART}: {len(repeated)} rows share an ({x}, {y}) pair, such as "
                         f"({first[x]:g}, {first[y]:g}); give one '{z}' per pair (aggregate first)")
    xs, ys = np.sort(rows[x].unique()).astype(float), np.sort(rows[y].unique()).astype(float)
    most = load_tokens()["surface"]["max_side"]
    for column, values in ((x, xs), (y, ys)):
        if not 2 <= len(values) <= most:
            raise ValueError(f"hairline: {CHART}: '{column}' needs 2 to {most} distinct values for a grid; got "
                             f"{len(values)}" + ("; bin it first" if len(values) > most else ""))
    grid = rows.pivot(index=y, columns=x, values=z).reindex(index=ys, columns=xs).to_numpy(dtype=float)
    return xs, ys, grid


def check_cells(grid: np.ndarray, z: str) -> None:
    """At least one cell with all four corners, or there is no surface to draw."""
    known = np.isfinite(grid)
    if not (known[:-1, :-1] & known[1:, :-1] & known[:-1, 1:] & known[1:, 1:]).any():
        raise ValueError(f"hairline: {CHART}: no cell of the grid has '{z}' at all four corners, so there is no "
                         f"surface to draw; fill the gaps or use a coarser grid")


def step_colors(colors: str | None, count: int) -> list[str]:
    """A colour per step: a sequential ramp without its lightest colour (which would vanish on the page), a
    diverging ramp from pole to pole."""
    name = colors or default_ramp("sequential")
    return ramp(name, count) if ramp_kind(name) == "diverging" else ramp(name, count + 1)[1:]


def ramp_position(value: float, limits: tuple[float, float], count: int) -> int:
    """The colour of `value` among `count` blended along the axis from its low to its high limit."""
    share = (value - limits[0]) / (limits[1] - limits[0])
    return min(count - 1, max(0, int(math.floor(share * (count - 1) + 0.5))))


def gradient_key(breaks: list[float], limits: tuple[float, float], colors: list[str]) -> dict:
    """The key of a gradient: the ramp's colour at each tick (every other tick when there are more than `max_bins`,
    so the key keeps to one row)."""
    steps = breaks if len(breaks) <= load_tokens()["surface"]["max_bins"] else breaks[::2]
    return {"colors": [colors[ramp_position(step, limits, len(colors))] for step in steps], "steps": list(steps),
            "limits": list(limits)}


def gradient_fills(grid: np.ndarray, limits: tuple[float, float], colors: list[str]) -> list[list[str | None]]:
    """Each cell's colour: its corners' mean on the ramp blended between the axis's limits; None for a cell with a
    corner missing."""
    means = np.stack([grid[:-1, :-1], grid[:-1, 1:], grid[1:, 1:], grid[1:, :-1]]).mean(axis=0)
    return [[None if not np.isfinite(mean) else colors[ramp_position(float(mean), limits, len(colors))]
             for mean in row] for row in means]


def surface_colors(grid: np.ndarray, breaks: list[float], colors: str | None, gradient: bool) -> dict:
    """The cells' colours and the key: bands of `color_steps()` by default, a blend along the ramp with `gradient`."""
    low, high = float(np.nanmin(grid)), float(np.nanmax(grid))
    if gradient:
        limits = (min(low, breaks[0]), max(high, breaks[-1]))
        blend = step_colors(colors, load_tokens()["surface"]["gradient_steps"])
        return {"fills": gradient_fills(grid, limits, blend), "key": gradient_key(breaks, limits, blend)}
    steps = color_steps(breaks, high)
    limits = (min(low, breaks[0]), max(high, breaks[-1], steps[-1]))
    colours = step_colors(colors, len(steps))
    return {"fills": cell_fills(grid, steps, colours), "key": {"colors": colours, "steps": steps,
                                                               "limits": list(limits)}}


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


def cell_fills(grid: np.ndarray, steps: list[float], colors: list[str]) -> list[list[str | None]]:
    """Each cell's colour: the step its corners' mean falls in; None for a cell with a corner missing."""
    corners = np.stack([grid[:-1, :-1], grid[:-1, 1:], grid[1:, 1:], grid[1:, :-1]])
    means = corners.mean(axis=0)
    return [[None if not np.isfinite(mean) else colors[step_index(float(mean), steps)] for mean in row]
            for row in means]


def axis_ticks(values: np.ndarray, percent: bool, locale: str, target: int) -> list[dict]:
    """Round values within the axis's range, placed on the cube's -1 to 1."""
    low, high = float(values.min()), float(values.max())
    inside = [tick for tick in nice_breaks(low, high, target) if low - 1e-9 <= tick <= high + 1e-9]
    return [{"at": 2 * (tick - low) / (high - low) - 1, "text": text}
            for tick, text in zip(inside, value_texts(inside, percent, locale), strict=True)]


def checked_view(elevation: float | None, azimuth: float | None) -> dict:
    rules = load_tokens()["surface"]
    low, high = rules["elevation_limits"]
    elevation = float(rules["elevation"] if elevation is None else elevation)
    if not low <= elevation <= high:
        raise ValueError(f"hairline: {CHART}: elevation {elevation:g} must lie between {low} and {high} degrees")
    azimuth = float(rules["azimuth"] if azimuth is None else azimuth)
    return {"elevation": elevation, "azimuth": (azimuth + 180) % 360 - 180}


def height_ticks(breaks: list[float], limits: tuple[float, float], height: float, percent: bool,
                 locale: str) -> list[dict]:
    """The value axis's breaks within its limits, placed on the cube's height (centred on zero)."""
    low, high = limits
    return [{"at": height * ((tick - low) / (high - low) - 0.5), "text": text}
            for tick, text in zip(breaks, value_texts(breaks, percent, locale), strict=True)]


def vertex_tips(xs: np.ndarray, ys: np.ndarray, grid: np.ndarray, percent: bool, locale: str) -> dict:
    """What a pointer on the surface reads in the HTML export: each grid point's x, y and value."""
    known = grid[np.isfinite(grid)]
    digits = auto_digits(known * 100 if percent else known)
    write = (lambda value: format_percent(snap_noise(value), digits, locale)) if percent else \
        (lambda value: format_number(snap_noise(value), digits, locale))
    return {"x": value_texts(xs, False, locale), "y": value_texts(ys, False, locale),
            "z": [[write(value) if np.isfinite(value) else "" for value in row] for row in grid]}


def surface_spec(data: pd.DataFrame, x: str, y: str, z: str, *, titles: dict[str, str], colors: str | None = None,
                 percent: bool = False, gradient: bool = False, view: dict | None = None) -> dict:
    """Everything the drawing needs, independent of the font: the grid in the cube (x and y from -1 to 1, z centred
    on zero), each cell's colour, ticks, titles, the steps of the colour key and the tooltip texts."""
    xs, ys, grid = surface_grid(data, x, y, z)
    check_cells(grid, z)
    rules, locale = load_tokens()["surface"], current_settings().locale
    breaks = nice_breaks(float(np.nanmin(grid)), float(np.nanmax(grid)), rules["ticks"])
    coloured = surface_colors(grid, breaks, colors, gradient)
    limits = coloured["key"]["limits"]
    height = rules["height"]
    normal = height * ((grid - limits[0]) / (limits[1] - limits[0]) - 0.5)
    return {"xs": (2 * (xs - xs[0]) / (xs[-1] - xs[0]) - 1).tolist(),
            "ys": (2 * (ys - ys[0]) / (ys[-1] - ys[0]) - 1).tolist(),
            "zs": [[float(value) if np.isfinite(value) else None for value in row] for row in normal],
            "fills": coloured["fills"], "height": height, "view": view or checked_view(None, None),
            "ticks": {"x": axis_ticks(xs, False, locale, rules["ticks"]),
                      "y": axis_ticks(ys, False, locale, rules["ticks"]),
                      "z": height_ticks(breaks, limits, height, percent, locale)},
            "titles": titles, "key": coloured["key"],
            "tips": vertex_tips(xs, ys, grid, percent, locale)}


def surface(data: pd.DataFrame, x: str, y: str, z: str, *, title: str | None = None, subtitle: str | None = None,
            caption: str | None = None, size: str = "onehalf", x_title: str | None = None,
            y_title: str | None = None, z_title: str | None = None, colors: str | None = None, percent: bool = False,
            gradient: bool = False, elevation: float | None = None,
            azimuth: float | None = None) -> HairlineFigure:
    """`z` over a grid of `x` and `y` (one row per pair; a pair without a row leaves a gap) as a 3D surface seen
    from `elevation` degrees above the floor, turned by `azimuth` degrees, its height binned into the steps of the
    ramp `colors` and keyed in the legend row; `gradient` blends each cell's colour along the ramp instead, and the
    key shows the ramp at each tick. `percent` reads `z` as shares. Turnable in the HTML export."""
    titles = {"x": x_title or humanise(x), "y": y_title or humanise(y), "z": z_title or humanise(z)}
    spec = surface_spec(data, x, y, z, titles=titles, colors=colors, percent=percent, gradient=gradient,
                        view=checked_view(elevation, azimuth))
    result = figure(title or titles["z"], subtitle=subtitle, caption=caption, size=size)
    result.draw(0, lambda box, measure, style: scene_shapes(surface_scene(spec, measure, style), box))
    result.scenes[0] = spec
    key = spec["key"]
    result.legend_ramp(key["colors"], key["steps"], titles["z"], format="percent" if percent else "number",
                       limits=tuple(key["limits"]))
    return fit_height(result)
