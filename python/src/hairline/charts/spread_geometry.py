"""Spread rows in pt: group names on the left, range line, interquartile band, median dot and reference tick on a
shared axis with grid lines, the key numbers right-aligned, the axis title under the numbers. Pure."""

from __future__ import annotations

from hairline.charts.donut_geometry import Measure, baseline_for, line_height, text
from hairline.charts.forest_geometry import axis_shapes, marker, x_scale
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens


def spread_columns(spec: dict, box: Box, measure: Measure, rules: dict, base: float) -> tuple[float, float]:
    """Left and right edge of the plot between the names and the numbers."""
    gap = rules["column_gap"] * base
    names = max(measure(row["name"], "label") for row in spec["rows"])
    numbers = max(measure(row["text"], "label") for row in spec["rows"])
    return box.x + names + gap, box.x + box.width - numbers - gap


def row_shapes(row: dict, centre: float, pitch: float, scale, style: dict, rules: dict) -> list[dict]:
    half = rules["band"] * pitch / 2
    band = [[scale(row["q1"]), centre - half], [scale(row["q3"]), centre - half], [scale(row["q3"]), centre + half],
            [scale(row["q1"]), centre + half]]
    shapes = [{"kind": "line", "points": [[scale(row["low"]), centre], [scale(row["high"]), centre]],
               "color": style["neutral"]["faint"], "width": style["leader_width"], "role": "range"},
              {"kind": "polygon", "points": band, "fill": row["color"], "alpha": rules["band_opacity"],
               "role": "band"},
              marker(scale(row["median"]), centre, rules["dot"] * style["base"], "dot", row["color"])]
    if row["mark"] is not None:
        tick, x = rules["mark"] * pitch / 2, scale(row["mark"])
        shapes.append({"kind": "line", "points": [[x, centre - tick], [x, centre + tick]],
                       "color": style["neutral"]["ink"], "width": style["leader_width"], "role": "mark"})
    return shapes


def axis_title_shape(spec: dict, right: float, axis_y: float, style: dict, rules: dict) -> list[dict]:
    if not spec["axis_title"]:
        return []
    size, base = style["sizes"]["label"], style["base"]
    ticks = axis_y + rules["axis_gap"] * base + style["cap_height"] * size
    gap = load_tokens()["spacing"]["x_title"] * base
    baseline = ticks + style["descender"] * size + gap + style["cap_height"] * size
    return [{**text(right, baseline, spec["axis_title"], "label", style["neutral"]["muted"], "right"), "part": "title"}]


def spread_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    rules, base, size = load_tokens()["spread"], style["base"], style["sizes"]["label"]
    left, right = spread_columns(spec, box, measure, rules, base)
    scale = x_scale(spec["axis"], False, left, right)
    reserve = rules["axis_gap"] * base + (style["cap_height"] + style["descender"]) * size
    if spec["axis_title"]:
        reserve += load_tokens()["spacing"]["x_title"] * base + (style["cap_height"] + style["descender"]) * size
    pitch = min(rules["row_pitch"] * line_height(style, "label"), (box.height - reserve) / len(spec["rows"]))
    bottom = box.y + pitch * len(spec["rows"])
    shapes = [{"kind": "line", "points": [[scale(value), box.y], [scale(value), bottom]],
               "color": style["neutral"]["grid"], "width": style["grid"], "role": "grid"}
              for value in spec["axis"]["breaks"]]
    for index, row in enumerate(spec["rows"]):
        centre = box.y + pitch * (index + 0.5)
        baseline = baseline_for(centre, style, "label")
        shapes += row_shapes(row, centre, pitch, scale, style, rules)
        shapes += [text(box.x, baseline, row["name"], "label", style["neutral"]["muted"]),
                   text(box.x + box.width, baseline, row["text"], "label", style["neutral"]["muted"], "right")]
    axis = {"axis": spec["axis"], "favours": None, "null": None}
    return shapes + axis_shapes(axis, scale, (left, right), bottom, style, rules) + \
        axis_title_shape(spec, right, bottom, style, rules)
