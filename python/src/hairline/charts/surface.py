"""Surface: one value over two numeric axes (time of day by week, dose by age), drawn as a turned 3D surface from a
fixed viewpoint, its height binned into the steps of a ramp and keyed in the legend row. It shows the shape at once;
exact values are read from a 2D chart beside it, and the HTML export lets the reader turn it."""

from __future__ import annotations

import numpy as np
import pandas as pd

from hairline.alt_text import described, grid_extremes
from hairline.charts.common import humanise
from hairline.charts.grid_values import color_scale, corner_means, fills, grid_tips, inner_ticks, read_grid, value_texts
from hairline.charts.heatmap import flat_spec
from hairline.charts.heatmap_geometry import heatmap_scene
from hairline.charts.surface_geometry import pair_layout, scene_shapes, surface_scene
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.settings import current_settings
from hairline.ticks import nice_breaks
from hairline.tokens import load_tokens

CHART = "surface"


def check_cells(grid: np.ndarray, z: str) -> None:
    """At least one cell with all four corners, or there is no surface to draw."""
    known = np.isfinite(grid)
    if not (known[:-1, :-1] & known[1:, :-1] & known[:-1, 1:] & known[1:, 1:]).any():
        raise ValueError(f"hairline: {CHART}: no cell of the grid has '{z}' at all four corners, so there is no "
                         f"surface to draw; fill the gaps or use a coarser grid")


def cube_ticks(values: np.ndarray, locale: str) -> list[dict]:
    """Round values within the axis's range, placed on the cube's -1 to 1."""
    low, high = float(values[0]), float(values[-1])
    return inner_ticks(low, high, locale, lambda tick: 2 * (tick - low) / (high - low) - 1)


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


def surface_spec(data: pd.DataFrame, x: str, y: str, z: str, *, titles: dict[str, str], colors: str | None = None,
                 percent: bool = False, gradient: bool = False, heatmap: bool = False,
                 view: dict | None = None) -> dict:
    """Everything the drawing needs, independent of the font: the grid in the cube (x and y from -1 to 1, z centred
    on zero), each cell's colour, ticks, titles, the steps of the colour key and the tooltip texts."""
    xs, ys, grid = read_grid(data, x, y, z, CHART)
    check_cells(grid, z)
    rules, locale = load_tokens()["surface"], current_settings().locale
    breaks = nice_breaks(float(np.nanmin(grid)), float(np.nanmax(grid)), rules["ticks"])
    scale = color_scale(grid, breaks, colors, gradient)
    limits = scale["key"]["limits"]
    height = rules["height"]
    normal = height * ((grid - limits[0]) / (limits[1] - limits[0]) - 0.5)
    tips = grid_tips(xs, ys, grid, percent, locale)
    return {"xs": (2 * (xs - xs[0]) / (xs[-1] - xs[0]) - 1).tolist(),
            "ys": (2 * (ys - ys[0]) / (ys[-1] - ys[0]) - 1).tolist(),
            "zs": [[float(value) if np.isfinite(value) else None for value in row] for row in normal],
            "fills": fills(corner_means(grid), scale), "height": height, "view": view or checked_view(None, None),
            "ticks": {"x": cube_ticks(xs, locale), "y": cube_ticks(ys, locale),
                      "z": height_ticks(breaks, limits, height, percent, locale)},
            "titles": titles, "key": scale["key"],
            "tips": tips, "description": described("kind_surface", grid_extremes(grid, tips, titles, locale), locale),
            **({"flat": flat_spec(xs, ys, grid, scale, titles, percent)} if heatmap else {})}


def surface_drawing(spec: dict):
    """The panel's drawing: the surface, or the surface and its heatmap side by side."""
    def draw(box, measure, style) -> list[dict]:
        scene = surface_scene(spec, measure, style)
        if "flat" not in spec:
            return scene_shapes(scene, box)
        return pair_layout(scene, heatmap_scene(spec["flat"], measure, style), box)["shapes"]
    return draw


def surface(data: pd.DataFrame, x: str, y: str, z: str, *, title: str | None = None, subtitle: str | None = None,
            caption: str | None = None, size: str | None = None, x_title: str | None = None,
            y_title: str | None = None, z_title: str | None = None, colors: str | None = None, percent: bool = False,
            gradient: bool = False, heatmap: bool = False, elevation: float | None = None,
            azimuth: float | None = None) -> HairlineFigure:
    """`z` over a grid of `x` and `y` (one row per pair; a pair without a row leaves a gap) as a 3D surface seen
    from `elevation` degrees above the floor, turned by `azimuth` degrees, its height binned into the steps of the
    ramp `colors` and keyed in the legend row; `gradient` blends each cell's colour along the ramp instead, and the
    key shows the ramp at each tick. `percent` reads `z` as shares. `heatmap` draws the values as a heatmap beside
    the surface, in the same colours (the double size by default): the surface shows the shape, the heatmap the
    values. Turnable in the HTML export, where pointing at either marks the same grid point in both."""
    titles = {"x": x_title or humanise(x), "y": y_title or humanise(y), "z": z_title or humanise(z)}
    spec = surface_spec(data, x, y, z, titles=titles, colors=colors, percent=percent, gradient=gradient,
                        heatmap=heatmap, view=checked_view(elevation, azimuth))
    result = figure(title or titles["z"], subtitle=subtitle, caption=caption,
                    size=size or ("double" if heatmap else "onehalf"))
    result.description = spec["description"]
    result.draw(0, surface_drawing(spec))
    result.scenes[0] = spec
    key = spec["key"]
    result.legend_ramp(key["colors"], key["steps"], titles["z"], format="percent" if percent else "number",
                       limits=tuple(key["limits"]))
    return fit_height(result)
