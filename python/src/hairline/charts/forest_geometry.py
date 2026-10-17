"""Forest plot geometry in pt: study table, intervals with weighted squares, pooled diamond, null and pooled
lines, and an x-axis (logarithmic for ratios) with "favours" labels. Pure, like the donut geometry."""

from __future__ import annotations

import math

from hairline.charts.donut_geometry import Measure, baseline_for, line_height, text
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens

SERIES = (1, 2, 5)


def log_breaks(low: float, high: float, max_ticks: int = 7) -> list[float]:
    """1-2-5 breaks covering [low, high]; powers of ten only when that gives more than `max_ticks`."""
    first, last = math.floor(math.log10(low)) - 1, math.ceil(math.log10(high)) + 1
    for series in (SERIES, (1,)):
        candidates = sorted(round(mantissa * 10 ** power, 10) for power in range(first, last + 1)
                            for mantissa in series)
        start = max(value for value in candidates if value <= low * (1 + 1e-9))
        end = min(value for value in candidates if value >= high * (1 - 1e-9))
        ticks = [value for value in candidates if start <= value <= end]
        if len(ticks) <= max_ticks:
            break
    return [int(value) if value == int(value) else value for value in ticks]


def x_scale(axis: dict, ratio: bool, left: float, right: float):
    def transform(value: float) -> float:
        return math.log(value) if ratio else value
    low, high = transform(axis["low"]), transform(axis["high"])
    return lambda value: left + (transform(value) - low) / (high - low) * (right - left)


def column_layout(spec: dict, box: Box, measure: Measure, rules: dict, base: float) -> dict:
    """Left edges of the study and extra columns, the plot span, right edges of effect and weight columns."""
    gap = rules["column_gap"] * base
    def widest(texts: list[str], weight: int | None = None) -> float:
        return max(measure(item, "label", weight) for item in texts)
    rows = spec["rows"]
    study = widest([spec["study_heading"]] + [row["study"] for row in rows] +
                   ([spec["pooled"]["label"]] if spec["pooled"] else []), 600)
    extras, x = [], box.x + study + gap
    for index, heading in enumerate(spec["columns"]):
        x += widest([heading] + [row["cells"][index] for row in rows])
        extras.append(x)
        x += gap
    effect = widest([spec["effect_heading"]] + [row["effect_text"] for row in rows] +
                    ([spec["pooled"]["effect_text"]] if spec["pooled"] else []))
    weight = widest([spec["weight_heading"]] + [row["weight_text"] for row in rows]) if spec["weight_heading"] else 0
    weight_right = box.x + box.width
    effect_right = weight_right - (weight + gap if spec["weight_heading"] else 0.0)
    return {"study": box.x, "extras": extras, "plot": (x, effect_right - effect - gap), "effect": effect_right,
            "weight": weight_right}


def row_centres(spec: dict, top: float, pitch: float, rules: dict) -> tuple[list[float], float | None]:
    centres = [top + pitch * (index + 0.5) for index in range(len(spec["rows"]))]
    pooled = top + pitch * (len(spec["rows"]) + 0.5) + rules["pooled_gap"] * pitch if spec["pooled"] else None
    return centres, pooled


def rule(left: float, right: float, y: float, style: dict) -> dict:
    return {"kind": "line", "points": [[left, y], [right, y]], "color": style["neutral"]["axis"],
            "width": style["leader_width"]}


def table_texts(spec: dict, columns: dict, baseline: float, row: dict | None, style: dict) -> list[dict]:
    """One table line: the headings when `row` is None, else study, cells, effect and weight of that row."""
    ink, muted = style["neutral"]["ink"], style["neutral"]["muted"]
    if row is None:
        values = [spec["study_heading"]] + spec["columns"] + [spec["effect_heading"], spec["weight_heading"]]
        colors, weights = [ink] * len(values), [600] * len(values)
    else:
        values = [row["study"]] + row["cells"] + [row["effect_text"], row.get("weight_text")]
        colors = [ink] + [muted] * len(row["cells"]) + [ink, muted]
        weights = [600 if row.get("bold") else None] + [None] * (len(values) - 1)
    rights = columns["extras"] + [columns["effect"], columns["weight"]]
    shapes = [text(columns["study"], baseline, values[0], "label", colors[0], "left", weights[0])]
    for value, right, color, weight in zip(values[1:], rights, colors[1:], weights[1:], strict=True):
        if value:
            shapes.append(text(right, baseline, value, "label", color, "right", weight))
    return shapes


def interval_marks(row: dict, centre: float, scale, plot: tuple[float, float], side: float, color: str,
                   style: dict) -> list[dict]:
    """Interval line clipped to the plot, and the square centred on the estimate."""
    left, right = max(plot[0], scale(row["low"])), min(plot[1], scale(row["high"]))
    x, half = scale(row["estimate"]), side / 2
    square = [[x - half, centre - half], [x + half, centre - half], [x + half, centre + half],
              [x - half, centre + half]]
    return [{"kind": "line", "points": [[left, centre], [right, centre]], "color": color, "width": style["data_width"]},
            {"kind": "polygon", "points": square, "fill": color, "role": "square"}]


def square_sides(spec: dict, rules: dict, base: float) -> list[float]:
    """Square area proportional to weight, the largest `max_square` wide; equal squares without weights."""
    weights = [row["weight"] for row in spec["rows"]]
    if any(weight is None for weight in weights):
        return [rules["plain_square"] * base] * len(weights)
    largest = max(weights)
    return [max(rules["min_square"] * base, rules["max_square"] * base * math.sqrt(weight / largest))
            for weight in weights]


def diamond(pooled: dict, centre: float, scale, half: float, style: dict) -> dict:
    points = [[scale(pooled["low"]), centre], [scale(pooled["estimate"]), centre - half],
              [scale(pooled["high"]), centre], [scale(pooled["estimate"]), centre + half]]
    return {"kind": "polygon", "points": points, "fill": style["neutral"]["ink"], "role": "diamond"}


def axis_shapes(spec: dict, scale, plot: tuple[float, float], y: float, style: dict, rules: dict) -> list[dict]:
    base, size, neutral = style["base"], style["sizes"]["label"], style["neutral"]
    shapes = [{"kind": "line", "points": [[plot[0], y], [plot[1], y]], "color": neutral["axis"],
               "width": style["axis_width"]}]
    tick_baseline = y + rules["axis_gap"] * base + style["cap_height"] * size
    for value, label in zip(spec["axis"]["breaks"], spec["axis"]["labels"], strict=True):
        shapes.append({**text(scale(value), tick_baseline, label, "label", neutral["muted"], "center"), "part": "tick"})
    if spec["favours"]:
        gap, null = rules["favours_gap"] * base, scale(spec["null"])
        baseline = tick_baseline + line_height(style, "label") + gap
        shapes += [{**text(null - gap, baseline, spec["favours"][0], "label", neutral["muted"], "right"),
                    "part": "favours"},
                   {**text(null + gap, baseline, spec["favours"][1], "label", neutral["muted"], "left"),
                    "part": "favours"}]
    return shapes


def pooled_shapes(spec: dict, columns: dict, top: float, bottom: float, pitch: float, centre: float, scale,
                  style: dict, rules: dict) -> list[dict]:
    """Rule above the pooled row, dashed pooled line, diamond and the pooled row's texts."""
    pooled = {**spec["pooled"], "study": spec["pooled"]["label"], "cells": [""] * len(spec["columns"]), "bold": True}
    divider, x = top + pitch * (len(spec["rows"]) + rules["pooled_gap"] / 2), scale(pooled["estimate"])
    return [rule(columns["study"], columns["weight"], divider, style),
            {"kind": "line", "points": [[x, top], [x, bottom]], "color": style["neutral"]["faint"],
             "width": style["leader_width"], "dash": rules["pooled_dash"]},
            diamond(pooled, centre, scale, rules["max_square"] * style["base"] / 2, style)] + table_texts(
        spec, columns, baseline_for(centre, style, "label"), pooled, style)


def forest_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    """Every shape of one forest plot inside `box` (pt from the figure's top-left corner)."""
    rules, base, size = load_tokens()["forest"], style["base"], style["sizes"]["label"]
    line = line_height(style, "label")
    columns = column_layout(spec, box, measure, rules, base)
    scale = x_scale(spec["axis"], spec["ratio"], *columns["plot"])
    heading = box.y + style["cap_height"] * size
    top = heading + line - style["cap_height"] * size + rules["rule_gap"] * base
    count = len(spec["rows"]) + (1 + rules["pooled_gap"] if spec["pooled"] else 0)
    reserve = rules["axis_gap"] * base * 2 + 2 * line + rules["favours_gap"] * base
    pitch = min(rules["row_pitch"] * line, (box.y + box.height - top - reserve) / count)
    centres, pooled_centre = row_centres(spec, top, pitch, rules)
    bottom = top + pitch * count
    shapes = table_texts(spec, columns, heading, None, style) + [rule(columns["study"], columns["weight"], top, style)]
    for row, centre, side in zip(spec["rows"], centres, square_sides(spec, rules, base), strict=True):
        shapes += table_texts(spec, columns, baseline_for(centre, style, "label"), row, style)
        shapes += interval_marks(row, centre, scale, columns["plot"], side, spec["color"], style)
    shapes.append({"kind": "line", "points": [[scale(spec["null"]), top], [scale(spec["null"]), bottom]],
                   "color": style["neutral"]["muted"], "width": style["leader_width"], "part": "null"})
    if spec["pooled"]:
        shapes += pooled_shapes(spec, columns, top, bottom, pitch, pooled_centre, scale, style, rules)
    return shapes + axis_shapes(spec, scale, columns["plot"], bottom + rules["axis_gap"] * base, style, rules)
