"""Funnel plot geometry in pt: the standard error runs down from 0 at the top, the pseudo 95 % region is a band
around the pooled line, the null line is solid; x axis below (logarithmic for ratios), y labels on the left."""

from __future__ import annotations

import math

from hairline.charts.donut_geometry import Measure, baseline_for, line_height, text
from hairline.layout.axes_style import edge_alignment
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens


def plot_area(spec: dict, box: Box, measure: Measure, style: dict) -> tuple[float, float, float, float]:
    spacing, base, line = load_tokens()["spacing"], style["base"], line_height(style, "label")
    widest = max(measure(label, "label") for label in spec["y_axis"]["labels"])
    left = box.x + widest + spacing["y_labels_plot"] * base
    top = box.y + line + load_tokens()["funnel"]["title_gap"] * base
    bottom = box.y + box.height - 2 * line - spacing["x_tick_pad"] * style["sizes"]["label"] - spacing["x_title"] * base
    return left, top, box.x + box.width, bottom


def scales(spec: dict, area: tuple[float, float, float, float]):
    left, top, right, bottom = area
    low, high = (math.log(spec["x_axis"][key]) if spec["ratio"] else spec["x_axis"][key] for key in ("low", "high"))
    def x(value: float) -> float:
        return left + (value - low) / (high - low) * (right - left)
    def y(value: float) -> float:
        return top + value / spec["y_axis"]["high"] * (bottom - top)
    return x, y


def axis_shapes(spec: dict, box: Box, area: tuple, x, y, style: dict) -> list[dict]:
    left, top, right, bottom = area
    neutral, spacing, size = style["neutral"], load_tokens()["spacing"], style["sizes"]["label"]
    shapes = [{**text(left - spacing["y_labels_plot"] * style["base"], baseline_for(y(value), style, "label"), label,
                      "label", neutral["muted"], "right"), "part": "y_label"}
              for value, label in zip(spec["y_axis"]["breaks"], spec["y_axis"]["labels"], strict=True)]
    shapes += [{"kind": "line", "points": [[left, y(value)], [right, y(value)]], "color": neutral["grid"],
                "width": style["grid"]} for value in spec["y_axis"]["breaks"] if value > 0]
    tick = bottom + spacing["x_tick_pad"] * size + style["cap_height"] * size
    for value, label in zip(spec["x_axis"]["breaks"], spec["x_axis"]["labels"], strict=True):
        position = x(math.log(value) if spec["ratio"] else value)
        shapes.append({**text(position, tick, label, "label", neutral["muted"],
                              edge_alignment((position - left) / (right - left))), "part": "x_label"})
    shapes.append(text(right, tick + line_height(style, "label") + spacing["x_title"] * style["base"],
                       spec["x_title"], "label", neutral["muted"], "right"))
    title_baseline = top - load_tokens()["funnel"]["title_gap"] * style["base"] - style["descender"] * size
    shapes.append(text(box.x, title_baseline, spec["y_title"], "label", neutral["muted"]))
    return shapes


def funnel_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    rules, neutral, base = load_tokens()["funnel"], style["neutral"], style["base"]
    area = plot_area(spec, box, measure, style)
    x, y = scales(spec, area)
    deepest, pooled = spec["y_axis"]["high"], spec["pooled"]
    region = [[x(pooled), y(0)], [x(pooled + rules["z"] * deepest), y(deepest)],
              [x(pooled - rules["z"] * deepest), y(deepest)]]
    shapes = [{"kind": "polygon", "points": region, "fill": neutral["band"], "role": "funnel"}]
    shapes += axis_shapes(spec, box, area, x, y, style)
    if spec["null"] is not None:
        shapes.append({"kind": "line", "points": [[x(spec["null"]), area[1]], [x(spec["null"]), area[3]]],
                       "color": neutral["muted"], "width": style["leader_width"], "part": "null"})
    shapes.append({"kind": "line", "points": [[x(pooled), area[1]], [x(pooled), area[3]]], "color": neutral["faint"],
                   "width": style["leader_width"], "dash": load_tokens()["forest"]["pooled_dash"], "part": "pooled"})
    shapes.append({"kind": "line", "points": [[area[0], area[3]], [area[2], area[3]]], "color": neutral["axis"],
                   "width": style["axis_width"]})
    radius = rules["point_radius"] * base
    for estimate, error in spec["points"]:
        centre = (x(estimate), y(error))
        shapes.append({"kind": "polygon", "role": "study", "fill": spec["color"], "alpha": rules["point_opacity"],
                       "points": [[centre[0] + radius * math.cos(2 * math.pi * step / 24),
                                   centre[1] + radius * math.sin(2 * math.pi * step / 24)] for step in range(24)]})
    return shapes
