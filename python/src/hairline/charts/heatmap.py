"""Heatmap: one value over two numeric axes as a grid of cells, one per (x, y) pair, coloured in the bands of a ramp
(or blended along it) and keyed in the legend row. The values to read beside a surface, or on their own."""

from __future__ import annotations

import numpy as np
import pandas as pd

from hairline.alt_text import described, grid_extremes
from hairline.charts.common import humanise
from hairline.charts.grid_values import color_scale, fills, grid_tips, inner_ticks, read_grid
from hairline.charts.heatmap_geometry import heatmap_scene, heatmap_shapes
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.settings import current_settings
from hairline.ticks import nice_breaks
from hairline.tokens import load_tokens

CHART = "heatmap"


def cell_edges(values: np.ndarray) -> np.ndarray:
    """Where the cells of sorted values meet: halfway between neighbours, half a step past the first and last."""
    middles = (values[:-1] + values[1:]) / 2
    return np.concatenate([[values[0] - (values[1] - values[0]) / 2], middles,
                           [values[-1] + (values[-1] - values[-2]) / 2]])


def edge_ticks(values: np.ndarray, edges: np.ndarray, locale: str) -> list[dict]:
    """Round values within the axis's range, placed on 0 to 1 from its first to its last cell edge."""
    low, high = float(edges[0]), float(edges[-1])
    return inner_ticks(float(values[0]), float(values[-1]), locale, lambda tick: (tick - low) / (high - low))


def flat_spec(xs: np.ndarray, ys: np.ndarray, grid: np.ndarray, scale: dict, titles: dict[str, str],
              percent: bool) -> dict:
    """The heatmap's part of a spec: cell edges on 0 to 1, each point's colour, ticks, titles and tooltip texts."""
    locale = current_settings().locale
    x_edges, y_edges = cell_edges(xs), cell_edges(ys)
    return {"x_edges": ((x_edges - x_edges[0]) / (x_edges[-1] - x_edges[0])).tolist(),
            "y_edges": ((y_edges - y_edges[0]) / (y_edges[-1] - y_edges[0])).tolist(),
            "fills": fills(grid, scale), "ticks": {"x": edge_ticks(xs, x_edges, locale),
                                                   "y": edge_ticks(ys, y_edges, locale)},
            "titles": titles, "tips": grid_tips(xs, ys, grid, percent, locale), "key": scale["key"]}


def heatmap_spec(data: pd.DataFrame, x: str, y: str, z: str, *, titles: dict[str, str], colors: str | None = None,
                 percent: bool = False, gradient: bool = False) -> dict:
    """Everything the heatmap draws, independent of the font."""
    xs, ys, grid = read_grid(data, x, y, z, CHART)
    breaks = nice_breaks(float(np.nanmin(grid)), float(np.nanmax(grid)), load_tokens()["surface"]["ticks"])
    spec = flat_spec(xs, ys, grid, color_scale(grid, breaks, colors, gradient), titles, percent)
    locale = current_settings().locale
    return {**spec, "description": described("kind_heatmap", grid_extremes(grid, spec["tips"], titles, locale),
                                             locale)}


def heatmap(data: pd.DataFrame, x: str, y: str, z: str, *, title: str | None = None, subtitle: str | None = None,
            caption: str | None = None, size: str = "onehalf", x_title: str | None = None,
            y_title: str | None = None, z_title: str | None = None, colors: str | None = None, percent: bool = False,
            gradient: bool = False) -> HairlineFigure:
    """`z` over a grid of `x` and `y` (one row per pair; a pair without a row is left blank) as one cell per pair,
    its value binned into the steps of the ramp `colors` and keyed in the legend row; `gradient` blends each cell's
    colour along the ramp instead. `percent` reads `z` as shares. In the HTML export a row highlights as one series
    and each cell names its x, y and value."""
    titles = {"x": x_title or humanise(x), "y": y_title or humanise(y), "z": z_title or humanise(z)}
    spec = heatmap_spec(data, x, y, z, titles=titles, colors=colors, percent=percent, gradient=gradient)
    result = figure(title or titles["z"], subtitle=subtitle, caption=caption, size=size)
    result.description = spec["description"]
    result.draw(0, lambda box, measure, style: heatmap_shapes(heatmap_scene(spec, measure, style), box))
    key = spec["key"]
    result.legend_ramp(key["colors"], key["steps"], titles["z"], format="percent" if percent else "number",
                       limits=tuple(key["limits"]))
    return fit_height(result)
