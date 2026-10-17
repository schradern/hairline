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
                         edgecolor="none", linewidth=0, alpha=shape.get("alpha", 1.0))
    elif shape["kind"] == "line":
        xs, ys = zip(*shape["points"], strict=True)
        artist = Line2D(xs, ys, transform=pt_transform(fig), color=shape["color"], linewidth=shape["width"],
                        linestyle=(0, tuple(shape["dash"])) if shape.get("dash") else "-", solid_capstyle="butt",
                        solid_joinstyle="miter")
    else:
        style = role_style(figure.settings, shape["role"], shape.get("weight"), shape["color"])
        return add_text(fig, shape["x"], shape["y"], shape["text"], style, shape["align"])
    artist.set_figure(fig)
    artist.set_in_layout(False)
    return artist


def run_drawings(figure: HairlineFigure) -> list:
    """Shapes of every drawn panel, for the plot boxes of the current layout."""
    style, measure, shapes = drawing_style(figure.settings), measure_for(figure.settings), []
    for index, draw in sorted(figure.drawings.items()):
        shapes += draw(figure.plot_boxes[index], measure, style)
    figure.shapes = shapes
    return [render_shape(figure, shape) for shape in shapes]


def text_positions(figure: HairlineFigure) -> list[list[float]]:
    return [[shape["x"], shape["y"]] for shape in figure.shapes if shape["kind"] == "text"]
