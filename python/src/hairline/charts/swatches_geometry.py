"""Swatch chart geometry in pt: colour sets grouped under headings, each a name and its use beside a row of
squares, sized to fit the width. Mirrored in R's swatches_drawing()."""

from __future__ import annotations

from hairline.charts.donut_geometry import Measure, baseline_for, line_height, text
from hairline.charts.tips import tagged
from hairline.color.vision import contrast
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens

RAMP_KINDS = ("sequential", "diverging")


def swatch_size(rows: list[dict], left: float, right: float, rules: dict, base: float) -> float:
    """The largest square up to the token size that fits the longest row; too narrow a figure is an error."""
    slots = max(len(row["colors"]) for row in rows)
    size = min(rules["swatch"] * base, (right - left - (slots - 1) * rules["gap_pt"]) / slots)
    if size < rules["min_swatch"] * base:
        raise ValueError(f"hairline: swatches: the figure is too narrow for {slots} colours in a row; use a wider "
                         "size or fewer sets")
    return size


def swatch_squares(row: dict, left: float, top: float, size: float, rules: dict, style: dict) -> list[dict]:
    """One tagged square per colour; near-white colours get an outline so they stay visible."""
    squares, step = [], "step " if row["kind"] in RAMP_KINDS else ""
    for index, color in enumerate(row["colors"]):
        x = left + index * (size + rules["gap_pt"])
        square = {"kind": "polygon", "role": "swatch", "fill": color,
                  "points": [[x, top], [x + size, top], [x + size, top + size], [x, top + size]]}
        if contrast(color, style["neutral"]["surface"]) < rules["edge_contrast"]:
            square |= {"edge": style["neutral"]["axis"], "edge_width": style["leader_width"]}
        squares.append(tagged(square, row["name"], f"{row['name']} {step}{index + 1}: {color}"))
    return squares


def swatches_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    rules, base, rows = load_tokens()["swatches"], style["base"], spec["rows"]
    ink, muted = style["neutral"]["ink"], style["neutral"]["muted"]
    labels = max(max(measure(row["name"], "label"), measure(row["use"], "label")) for row in rows)
    left = box.x + labels + rules["column_gap"] * base
    size = swatch_size(rows, left, box.x + box.width, rules, base)
    label_line, heading_line = line_height(style, "label"), line_height(style, "panel")
    block = max(size, 2 * label_line)
    shapes, y, kind = [], box.y, None
    for row in rows:
        if row["kind"] != kind:
            y += 0.0 if kind is None else rules["group_gap"] * base
            shapes.append(text(box.x, baseline_for(y + heading_line / 2, style, "panel"),
                               rules["headings"][row["kind"]], "panel", ink))
            y, kind = y + heading_line + rules["heading_gap"] * base, row["kind"]
        shapes.append(text(box.x, baseline_for(y + label_line / 2, style, "label"), row["name"], "label", ink))
        shapes.append(text(box.x, baseline_for(y + label_line * 1.5, style, "label"), row["use"], "label", muted))
        shapes += swatch_squares(row, left, y + (block - size) / 2, size, rules, style)
        y += block + rules["row_gap"] * base
    return shapes
