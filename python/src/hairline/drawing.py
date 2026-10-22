"""Charts drawn in pt (donut, partition bars, Sankey): shared shape lists rendered as frame artists.

A chart registers a function that receives its panel's plot box, a text-measuring function and the style,
and returns shapes: polygons, lines and texts, all in pt from the figure's top-left corner.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from matplotlib.lines import Line2D
from matplotlib.patches import Polygon

from hairline.layout.draw import add_text, pt_transform
from hairline.layout.geometry import load_font_metrics
from hairline.layout.measure import text_width
from hairline.layout.styles import role_style
from hairline.marks import line_scale
from hairline.settings import Settings, role_size
from hairline.tokens import load_tokens

if TYPE_CHECKING:
    from hairline.figure import HairlineFigure


def drawing_style(settings: Settings) -> dict:
    tokens = load_tokens()
    spacing, base = tokens["spacing"], settings.base_size
    return {"base": base, "sizes": {role: role_size(settings, role) for role in tokens["type"]["roles"]},
            "line_gap": tokens["type"]["line_gap"], "cap_height": load_font_metrics().cap_height,
            "neutral": dict(settings.neutral), "swatch": spacing["legend_swatch_square"],
            "swatch_text": spacing["legend_swatch_text"], "leader_width": tokens["reference"]["width"] * base,
            "data_width": tokens["lines"]["data"] * base, "axis_width": tokens["lines"]["axis"] * base,
            "grid": tokens["lines"]["grid"] * base,
            "descender": load_font_metrics().descender}


def measure_for(settings: Settings):
    def measure(text: str, role: str, weight: int | None = None) -> float:
        style = role_style(settings, role, weight)
        return text_width(text, style["family"], style["size"], style["weight"])
    return measure


def render_shape(figure: HairlineFigure, shape: dict):
    fig = figure.figure
    if shape["kind"] == "polygon":
        artist = Polygon(shape["points"], closed=True, transform=pt_transform(fig), facecolor=shape["fill"],
                         edgecolor=shape.get("edge", "none"), linewidth=shape.get("edge_width", 0),
                         alpha=shape.get("alpha", 1.0), joinstyle="miter")
    elif shape["kind"] == "line":
        xs, ys = zip(*shape["points"], strict=True)
        artist = Line2D(xs, ys, transform=pt_transform(fig), color=shape["color"], linewidth=shape["width"],
                        linestyle=(0, tuple(shape["dash"])) if shape.get("dash") else "-", solid_capstyle="butt",
                        solid_joinstyle="round", alpha=shape.get("alpha", 1.0))
    else:
        style = role_style(figure.settings, shape["role"], shape.get("weight"), shape["color"])
        artist = add_text(fig, shape["x"], shape["y"], shape["text"], style, shape["align"])
        if shape.get("rotation"):
            artist.set_rotation(shape["rotation"])
            artist.set_rotation_mode("anchor")
        return artist
    artist.set_figure(fig)
    artist.set_in_layout(False)
    return artist


def run_drawings(figure: HairlineFigure) -> list:
    """Shapes of every drawn panel, for the plot boxes of the current layout."""
    style, measure, shapes = drawing_style(figure.settings), measure_for(figure.settings), []
    for index, draw in sorted(figure.drawings.items()):
        box = figure.plot_boxes[index]
        shapes += draw(box, measure, {**style, "data_width": style["data_width"] * line_scale(box.width)})
    figure.shapes = shapes
    return [render_shape(figure, shape) for shape in shapes]


def text_positions(figure: HairlineFigure) -> list[list[float]]:
    return [[shape["x"], shape["y"]] for shape in figure.shapes if shape["kind"] == "text"]


def content_bottom(shapes: list[dict], style: dict, measure=None) -> float:
    """Lowest point the shapes reach: outlines, texts down to their descenders, and a text turned upright (rotated
    90°, anchored at its end) down to its start, its length below the anchor."""
    bottoms = []
    for shape in shapes:
        if shape["kind"] == "text":
            if shape.get("rotation"):
                upright = shape["rotation"] == 90 and shape.get("align") == "right" and measure is not None
                descent = measure(shape["text"], shape["role"], shape.get("weight")) if upright else 0.0
            else:
                descent = style["descender"] * style["sizes"][shape["role"]]
            bottoms.append(shape["y"] + descent)
        else:
            bottoms.append(max(point[1] for point in shape["points"]))
    return max(bottoms)


# Passes of a grow-only fit: a taller panel can move content (a larger donut moves its key), so it is fitted again.
GROW_PASSES = 4
# Overflow in pt a grow-only fit ignores: a donut's lowest arc point may sit a rounding error past its panel.
GROW_SLACK = 0.01


def fit_height(figure: HairlineFigure, shrink: bool = True) -> HairlineFigure:
    """Resize the figure so its drawn panel ends where the content ends (shorter, or taller when it overflows).
    With `shrink` False the figure only grows, for charts that fill their panel unless their labels need more.
    Only the frame is laid out, in pt: a full draw would rasterise the provisional figure, whose pixels grow with
    the square of its width."""
    for _ in range(1 if shrink else GROW_PASSES):
        figure.figure.get_layout_engine().execute(figure.figure)
        box = figure.plot_boxes[0]
        slack = box.y + box.height - content_bottom(figure.shapes, drawing_style(figure.settings),
                                                    measure_for(figure.settings))
        if not shrink and slack > -GROW_SLACK:
            break
        width, height = figure.figure.get_size_inches()
        figure.figure.set_size_inches(width, height - slack / 72)
    return figure


def keep_plot_height(figure: HairlineFigure, least: float) -> HairlineFigure:
    """Make the figure taller when its frame (title, legend, header, axis, table) would leave a panel less than
    `least` pt high: the frame keeps its size, the plot its room. Only the frame is laid out, at a probe height
    tall enough for any frame of this width; nothing is drawn."""
    width, height = figure.figure.get_size_inches()
    probe = 2 * height + least / 72
    figure.figure.set_size_inches(width, probe)
    figure.figure.get_layout_engine().execute(figure.figure)
    rows = len({box.y for box in figure.plot_boxes})
    frame = probe * 72 - rows * min(box.height for box in figure.plot_boxes)
    figure.figure.set_size_inches(width, max(height, (frame + rows * least) / 72))
    return figure
