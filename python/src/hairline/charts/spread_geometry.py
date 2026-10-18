"""Spread rows in pt: group names on the left, range line, interquartile band, median dot and reference tick on a
shared axis with grid lines, the key numbers right-aligned, the axis title under the numbers. Pure."""

from __future__ import annotations

from hairline.charts.donut_geometry import Measure, baseline_for, line_height, text
from hairline.charts.forest_geometry import axis_shapes, dot_size, marker, x_scale
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens


def pair_width(pair: list[str], measure: Measure) -> float:
    return measure(f"{pair[0]} ", "label") + measure(pair[1], "label", load_tokens()["type"]["value_weight"])


def stat_columns(spec: dict, right: float, measure: Measure, style: dict) -> list[float]:
    """Left edges of the key-number columns, the block ending at `right`: one column per statistic, so labels
    line up from row to row; columns are separated like a panel header's key numbers."""
    gap = load_tokens()["spacing"]["stats_pair"] * style["base"]
    count = max(len(row["pairs"]) for row in spec["rows"])
    widths = [max((pair_width(row["pairs"][index], measure) for row in spec["rows"] if index < len(row["pairs"])),
                  default=0.0) for index in range(count)]
    lefts, x = [], right - sum(widths) - gap * (count - 1)
    for width in widths:
        lefts.append(x)
        x += width + gap
    return lefts


def pair_texts(pairs: list[list[str]], lefts: list[float], baseline: float, measure: Measure,
               style: dict) -> list[dict]:
    """Label in faint, value in muted at the value weight: the panel header's key-number style."""
    neutral, weight, shapes = style["neutral"], load_tokens()["type"]["value_weight"], []
    for (label, value), left in zip(pairs, lefts, strict=False):
        shapes += [text(left, baseline, f"{label} ", "label", neutral["faint"]),
                   text(left + measure(f"{label} ", "label"), baseline, value, "label", neutral["muted"], "left",
                        weight)]
    return shapes


def spread_columns(spec: dict, box: Box, measure: Measure, rules: dict, base: float,
                   lefts: list[float]) -> tuple[float, float]:
    """Left and right edge of the plot between the names and the key numbers."""
    names = max(measure(row["name"], "label") for row in spec["rows"])
    return box.x + names + rules["column_gap"] * base, lefts[0] - rules["column_gap"] * base


def row_shapes(row: dict, centre: float, pitch: float, scale, style: dict, rules: dict) -> list[dict]:
    half = rules["band"] * pitch / 2
    band = [[scale(row["q1"]), centre - half], [scale(row["q3"]), centre - half], [scale(row["q3"]), centre + half],
            [scale(row["q1"]), centre + half]]
    tip = f"{row['name']}: " + ", ".join(f"{label} {value}" for label, value in row["pairs"])
    shapes = [{"kind": "line", "points": [[scale(row["low"]), centre], [scale(row["high"]), centre]],
               "color": style["neutral"]["faint"], "width": style["leader_width"], "role": "range"},
              {"kind": "polygon", "points": band, "fill": row["color"], "alpha": rules["band_opacity"],
               "role": "band", "tip": tip, "tip_at": [scale(row["median"]), centre - half]},
              marker(scale(row["median"]), centre, dot_size(style), "dot", row["color"])]
    if row["mark"] is not None:
        tick, x = rules["mark"] * half, scale(row["mark"])
        shapes.append({"kind": "line", "points": [[x, centre - tick], [x, centre + tick]],
                       "color": style["neutral"]["ink"], "width": style["leader_width"], "role": "mark"})
    return [{**shape, "series": row["name"]} for shape in shapes]


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
    lefts = stat_columns(spec, box.x + box.width, measure, style)
    left, right = spread_columns(spec, box, measure, rules, base, lefts)
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
        shapes += [text(box.x, baseline, row["name"], "label", style["neutral"]["ink"])]
        shapes += pair_texts(row["pairs"], lefts, baseline, measure, style)
    axis = {"axis": spec["axis"], "favours": None, "null": None}
    return shapes + axis_shapes(axis, scale, (left, right), bottom, style, rules) + \
        axis_title_shape(spec, right, bottom, style, rules)
