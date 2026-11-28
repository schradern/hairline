"""Heatmap geometry in pt: one cell per grid point, its edges halfway to the neighbouring values, its axis text where
the frame puts an axis chart's (the spacing tokens: y labels, x tick band and pad, axis titles), so it reads as
one with the other charts. Pure;
mirrored in R's heatmap_geometry.R. Beside a surface (`surface(heatmap=True)`) it shares the surface's height and
leaves its cells untagged, since the surface's script links the two."""

from __future__ import annotations

from hairline.charts.donut_geometry import Measure, text
from hairline.charts.heatmap_margins import margin_reserve, margin_scene, margin_shapes
from hairline.charts.tips import tagged
from hairline.errors import HairlineLayoutError
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens


def heatmap_scene(spec: dict, measure: Measure, style: dict) -> dict:
    """The flat spec with every text's width in pt, and the colours, sizes and gaps the drawing needs: those the
    frame gives an axis chart."""
    neutral, size, base, tokens = style["neutral"], style["sizes"]["label"], style["base"], load_tokens()
    spacing = tokens["spacing"]
    ticks = {axis: [{**tick, "width": measure(tick["text"], "label")} for tick in spec["ticks"][axis]]
             for axis in ("x", "y")}
    return {"x_edges": spec["x_edges"], "y_edges": spec["y_edges"], "fills": spec["fills"], "tips": spec["tips"],
            "titles": {axis: spec["titles"][axis] for axis in ("x", "y")}, "ticks": ticks,
            "text": {"cap": style["cap_height"] * size, "descender": style["descender"] * size,
                     "ascender": style["ascender"] * size, "ticks": neutral["faint"], "titles": neutral["muted"]},
            "gaps": {"y_labels": spacing["y_labels_plot"] * base, "x_pad": spacing["x_tick_pad"] * size,
                     "x_band": spacing["x_tick_labels"] * size, "x_title": spacing["x_title"] * base,
                     "y_title": spacing["y_title"] * base},
            "seam": tokens["surface"]["seam_pt"], "aspect": tokens["heatmap"]["aspect"],
            "margins": margin_scene(spec.get("margins"), measure, style)}


def plot_frame(scene: dict, box: Box, height: float | None) -> Box:
    """The cells' rectangle: right of the y ticks, under the y title (and the marginal bars), above the x tick band
    and title, as the frame places an axis chart's; its height `height` less the text rows, or the width times the
    aspect (at most what the box allows, unless bars grow the figure)."""
    glyphs, gaps = scene["text"], scene["gaps"]
    line = glyphs["cap"] + glyphs["descender"]
    above, beside = margin_reserve(scene["margins"], line)
    left = box.x + max((tick["width"] for tick in scene["ticks"]["y"]), default=0.0) + gaps["y_labels"]
    top = box.y + (line + gaps["y_title"] if scene["titles"]["y"] else glyphs["cap"] / 2)
    below = gaps["x_band"] + (gaps["x_title"] + line if scene["titles"]["x"] else 0.0)
    last = scene["ticks"]["x"][-1]["width"] / 2 if scene["ticks"]["x"] else 0.0
    width = box.x + box.width - max(last, beside) - left
    room = (box.height if height is None else height) - (top - box.y) - below
    tall = room if height is not None else min(room, width * scene["aspect"])
    if scene["margins"] is not None and height is None:
        # The bars add to the figure's height (fit_height() grows it) rather than take it from the cells, which keep
        # the aspect whatever the box: a height read from the box would grow with the figure again.
        tall = width * scene["aspect"]
    top += above
    if width <= 0 or tall <= 0:
        raise HairlineLayoutError(f"hairline: heatmap: the axis labels leave no room for the cells in "
                                  f"{box.width:.0f} x {box.height:.0f} pt. Shorten the labels or use a wider size")
    return Box(left, top, width, tall)


def cell_shapes(scene: dict, plot: Box, tag: bool) -> tuple[list[dict], list[list[float]]]:
    """A rectangle per grid point with a value, and its [x, y, width, height, column, row] for the script."""
    shapes, cells = [], []
    xs, ys, tips, titles = scene["x_edges"], scene["y_edges"], scene["tips"], scene["titles"]
    for row in range(len(ys) - 1):
        for column in range(len(xs) - 1):
            fill = scene["fills"][row][column]
            if fill is None:
                continue
            left, right = plot.x + xs[column] * plot.width, plot.x + xs[column + 1] * plot.width
            top, bottom = plot.y + (1 - ys[row + 1]) * plot.height, plot.y + (1 - ys[row]) * plot.height
            shape = {"kind": "polygon", "points": [[left, top], [right, top], [right, bottom], [left, bottom]],
                     "fill": fill, "edge": fill, "edge_width": scene["seam"], "part": "cell"}
            if tag:
                where = " ".join(part for part in (titles["y"], tips["y"][row]) if part)
                tip = f"{' '.join(part for part in (titles['x'], tips['x'][column]) if part)}, {where}: " \
                      f"{tips['z'][row][column]}"
                shape = tagged(shape, where, tip)
            shapes.append(shape)
            cells.append([left, top, right - left, bottom - top, column, row])
    return shapes, cells


def heatmap_layout(scene: dict, box: Box, height: float | None = None,
                   tag: bool = True) -> tuple[list[dict], list[list[float]]]:
    """Cells, the marginal bars, then tick labels and titles; and the cells' rectangles for the script."""
    plot = plot_frame(scene, box, height)
    shapes, cells = cell_shapes(scene, plot, tag)
    shapes += margin_shapes(scene, plot)
    glyphs, gaps = scene["text"], scene["gaps"]
    for tick in scene["ticks"]["y"]:
        y = plot.y + (1 - tick["at"]) * plot.height
        shapes.append({**text(plot.x - gaps["y_labels"], y + glyphs["cap"] / 2, tick["text"], "label", glyphs["ticks"],
                              "right"), "part": "tick"})
    bottom = plot.y + plot.height
    baseline = bottom + gaps["x_pad"] + glyphs["ascender"]
    for tick in scene["ticks"]["x"]:
        shapes.append({**text(plot.x + tick["at"] * plot.width, baseline, tick["text"], "label", glyphs["ticks"],
                              "center"), "part": "tick"})
    if scene["titles"]["y"]:
        shapes.append({**text(box.x, box.y + glyphs["cap"], scene["titles"]["y"], "label", glyphs["titles"]),
                       "part": "title"})
    if scene["titles"]["x"]:
        below = bottom + gaps["x_band"] + gaps["x_title"] + glyphs["cap"]
        shapes.append({**text(plot.x + plot.width, below, scene["titles"]["x"], "label", glyphs["titles"], "right"),
                       "part": "title"})
    return shapes, cells


def heatmap_shapes(scene: dict, box: Box) -> list[dict]:
    """The standalone heatmap, each cell a tooltip target of its row."""
    return heatmap_layout(scene, box)[0]
