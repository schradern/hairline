"""Forest plot geometry in pt: study table, intervals with weighted squares, pooled diamond, null and pooled
lines, and an x-axis (logarithmic for ratios) with "favours" labels. Pure, like the donut geometry."""

from __future__ import annotations

import math

from hairline.charts.donut_geometry import Measure, baseline_for, line_height, text
from hairline.errors import HairlineLayoutError
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens

SERIES = (1, 2, 5)


# Ratio breaks are rounded to this many decimals, so a ratio axis reaches from 10^-RATIO_PLACES to 10^RATIO_PLACES.
RATIO_PLACES = 10


def log_breaks(low: float, high: float, max_ticks: int = 7) -> list[float]:
    """1-2-5 breaks covering [low, high]; powers of ten only when that gives more than `max_ticks`."""
    first, last = math.floor(math.log10(low)) - 1, math.ceil(math.log10(high)) + 1
    for series in (SERIES, (1,)):
        candidates = sorted(round(mantissa * 10 ** power, RATIO_PLACES) for power in range(first, last + 1)
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


def column_widths(spec: dict, measure: Measure) -> tuple[float, list[float], float, float]:
    """Widths of the study column, the extra columns, the effect column and the weight column (0 without)."""
    def widest(texts: list[str], weight: int | None = None) -> float:
        return max(measure(item, "label", weight) for item in texts)
    rows = spec["rows"]
    study = widest([spec["study_heading"]] + [row["study"] for row in rows] +
                   ([spec["pooled"]["label"]] if spec["pooled"] else []))
    extras = [widest([heading] + [row["cells"][index] for row in rows])
              for index, heading in enumerate(spec["columns"])]
    effect = max(widest([spec["effect_heading"]] + [row["effect_text"] for row in rows]),
                 widest([spec["pooled"]["effect_text"]], 600) if spec["pooled"] else 0.0)
    weight = widest([spec["weight_heading"]] + [row["weight_text"] for row in rows]) if spec["weight_heading"] else 0
    return study, extras, effect, weight


def right_edges(widths: list[float], start: float, gap: float) -> list[float]:
    edges, x = [], start
    for width in widths:
        x += width
        edges.append(x)
        x += gap
    return edges


def column_layout(spec: dict, box: Box, measure: Measure, rules: dict, base: float) -> dict:
    """Left edge of the study column, right edges of the extra, effect and weight columns and the plot span. The
    columns sit beside the plot while it keeps `min_plot`; on a narrower figure they move to a line under each row
    (`under`), from the study column's left edge, and the plot spans the width the study labels leave."""
    gap, least, right = rules["column_gap"] * base, rules["min_plot"] * base, box.x + box.width
    study, extras, effect, weight = column_widths(spec, measure)
    weighted = bool(spec["weight_heading"])
    beside = right_edges(extras, box.x + study + gap, gap)
    plot_left = beside[-1] + gap if beside else box.x + study + gap
    effect_right = right - (weight + gap if weighted else 0.0)
    if effect_right - effect - gap - plot_left >= least:
        return {"study": box.x, "extras": beside, "plot": (plot_left, effect_right - effect - gap),
                "effect": effect_right, "weight": right, "right": right, "under": False}
    widths = extras + [effect] + ([weight] if weighted else [])
    check_room(box.width, sum(widths) + gap * (len(widths) - 1), least, study, gap)
    under = right_edges(widths, box.x, gap)
    return {"study": box.x, "extras": under[:len(extras)], "plot": (box.x + study + gap, right),
            "effect": under[len(extras)], "weight": under[-1] if weighted else right, "right": right, "under": True}


def check_room(width: float, block: float, least: float, study: float, gap: float) -> None:
    """Under the rows, a line of columns and a row of study label and intervals must each fit the width."""
    need = max(block, study + gap + least)
    if width < need:
        raise HairlineLayoutError(f"hairline: forest: the figure leaves {width:.0f} pt for the table, which needs at "
                                  f"least {need:.0f} pt: the columns take {block:.0f} pt in one line under each "
                                  f"study, the study labels {study:.0f} pt beside intervals of {least:.0f} pt. "
                                  "Shorten the longest study labels, drop a column, or use a wider size")


def row_centres(spec: dict, top: float, pitch: float, line_pitch: float, rules: dict) -> tuple[list[float],
                                                                                                float | None]:
    """Centres of the study rows and the pooled row; a row whose columns sit under it is a line taller (`pitch`
    over `line_pitch`), and its interval stays on its first line."""
    centres = [top + pitch * index + line_pitch / 2 for index in range(len(spec["rows"]))]
    pooled = top + pitch * len(spec["rows"]) + line_pitch / 2 + rules["pooled_gap"] * pitch if spec["pooled"] \
        else None
    return centres, pooled


def rule(left: float, right: float, y: float, style: dict) -> dict:
    return {"kind": "line", "points": [[left, y], [right, y]], "color": style["neutral"]["axis"],
            "width": style["leader_width"]}


def table_texts(spec: dict, columns: dict, baseline: float, row: dict | None, style: dict) -> list[dict]:
    """One table row: the headings when `row` is None, else study, cells, effect and weight of that row; the
    columns after the study label one line lower (`lead`) when they sit under the row."""
    ink, muted = style["neutral"]["ink"], style["neutral"]["muted"]
    if row is None:
        values = [spec["study_heading"]] + spec["columns"] + [spec["effect_heading"], spec["weight_heading"]]
        colors, weights = [muted] * len(values), [None] * len(values)
    else:
        values = [row["study"]] + row["cells"] + [row["effect_text"], row.get("weight_text")]
        colors = [ink] + [muted] * len(row["cells"]) + [ink, muted]
        weights = [None] * (len(values) - 2) + [600 if row.get("bold") else None, None]
    rights, lead = columns["extras"] + [columns["effect"], columns["weight"]], columns.get("lead", 0.0)
    shapes = [text(columns["study"], baseline, values[0], "label", colors[0], "left", weights[0])]
    for value, right, color, weight in zip(values[1:], rights, colors[1:], weights[1:], strict=True):
        if value:
            shapes.append(text(right, baseline + lead, value, "label", color, "right", weight))
    return shapes


def marker(x: float, centre: float, side: float, shape: str, color: str) -> dict:
    """A square of side `side`, or a dot of that diameter (24-point polygon)."""
    half = side / 2
    if shape == "dot":
        points = [[x + half * math.cos(2 * math.pi * step / 24), centre + half * math.sin(2 * math.pi * step / 24)]
                  for step in range(24)]
        return {"kind": "polygon", "points": points, "fill": color, "role": "dot"}
    square = [[x - half, centre - half], [x + half, centre - half], [x + half, centre + half],
              [x - half, centre + half]]
    return {"kind": "polygon", "points": square, "fill": color, "role": "square"}


def interval_marks(row: dict, centre: float, scale, plot: tuple[float, float], side: float, spec: dict,
                   style: dict) -> list[dict]:
    """Interval line clipped to the plot, and the marker centred on the estimate."""
    left, right = max(plot[0], scale(row["low"])), min(plot[1], scale(row["high"]))
    line = {"kind": "line", "points": [[left, centre], [right, centre]], "color": spec["color"],
            "width": style["data_width"], "series": row["study"]}
    tip = {"series": row["study"], "tip": f"{row['study']}: {row['effect_text']}",
           "tip_at": [scale(row["estimate"]), centre - side / 2]}
    return [line, {**marker(scale(row["estimate"]), centre, side, spec.get("marker", "square"), spec["color"]),
                   **tip}]


def dot_size(style: dict) -> float:
    """Diameter of a dot mark: the same as a scatter point, in every chart."""
    return 2 * load_tokens()["lines"]["point_radius"] * style["base"]


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
    if spec["favours"] and spec["null"] is not None:
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
    return [rule(columns["study"], columns["right"], divider, style),
            {"kind": "line", "points": [[x, top], [x, bottom]], "color": style["neutral"]["faint"],
             "width": style["leader_width"], "dash": rules["pooled_dash"]},
            diamond(pooled, centre, scale, rules["max_square"] * style["base"] / 2, style)] + table_texts(
        spec, columns, baseline_for(centre, style, "label"), pooled, style)


def forest_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    """Every shape of one forest plot inside `box` (pt from the figure's top-left corner)."""
    rules, base, size = load_tokens()["forest"], style["base"], style["sizes"]["label"]
    line = line_height(style, "label")
    columns = column_layout(spec, box, measure, rules, base)
    columns["lead"] = line if columns["under"] else 0.0
    scale = x_scale(spec["axis"], spec["ratio"], *columns["plot"])
    heading = box.y + style["cap_height"] * size
    top = heading + line - style["cap_height"] * size + rules["rule_gap"] * base + columns["lead"]
    count = len(spec["rows"]) + (1 + rules["pooled_gap"] if spec["pooled"] else 0)
    # Rows keep their pitch; the figure's height follows them (fit_height), so many rows never overlap.
    line_pitch = rules["row_pitch"] * line
    pitch = line_pitch + columns["lead"]
    centres, pooled_centre = row_centres(spec, top, pitch, line_pitch, rules)
    bottom = top + pitch * count
    shapes = table_texts(spec, columns, heading, None, style) + [rule(columns["study"], columns["right"], top, style)]
    sides = [dot_size(style)] * len(spec["rows"]) if spec.get("marker") == "dot" else square_sides(spec, rules, base)
    for row, centre, side in zip(spec["rows"], centres, sides, strict=True):
        shapes += table_texts(spec, columns, baseline_for(centre, style, "label"), row, style)
        shapes += interval_marks(row, centre, scale, columns["plot"], side, spec, style)
    if spec["null"] is not None:
        shapes.append({"kind": "line", "points": [[scale(spec["null"]), top], [scale(spec["null"]), bottom]],
                       "color": style["neutral"]["muted"], "width": style["leader_width"], "part": "null"})
    if spec["pooled"]:
        shapes += pooled_shapes(spec, columns, top, bottom, pitch, pooled_centre, scale, style, rules)
    return shapes + axis_shapes(spec, scale, columns["plot"], bottom + rules["axis_gap"] * base, style, rules)
