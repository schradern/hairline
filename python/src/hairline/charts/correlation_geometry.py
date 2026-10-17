"""Correlation heatmap geometry in pt: the lower triangle without the diagonal, each variable named on the empty
diagonal (one label serves its row and its column), values printed in the cells. Pure, like the donut geometry."""

from __future__ import annotations

from hairline.charts.donut_geometry import Measure, baseline_for, text
from hairline.color.vision import contrast
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens


def cell_side(spec: dict, box: Box, measure: Measure, style: dict, rules: dict) -> float:
    """Square cells, as large as the box allows but at most `max_cell` times the base size."""
    count = len(spec["names"])
    widest = max(measure(name, "label") for name in spec["names"])
    return min(rules["max_cell"] * style["base"], box.height / count, (box.width - widest) / count)


def text_color(fill: str, style: dict) -> str:
    neutral = style["neutral"]
    dark = contrast(fill, neutral["ink"]) >= contrast(fill, neutral["surface"])
    return neutral["ink"] if dark else neutral["surface"]


def correlation_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    rules = load_tokens()["correlation"]
    side, inset = cell_side(spec, box, measure, style, rules), rules["gap_pt"] / 2
    cells, values, names = [], [], []
    for row, name in enumerate(spec["names"]):
        top = box.y + row * side
        for column in range(row):
            left, fill = box.x + column * side, spec["colors"][row][column]
            cells.append({"kind": "polygon", "role": "cell", "fill": fill,
                          "points": [[left + inset, top + inset], [left + side - inset, top + inset],
                                     [left + side - inset, top + side - inset], [left + inset, top + side - inset]]})
            values.append({**text(left + side / 2, baseline_for(top + side / 2, style, "label"),
                                  spec["texts"][row][column], "label", text_color(fill, style), "center"),
                           "part": "value"})
        names.append({**text(box.x + row * side + rules["label_gap"] * style["base"],
                             baseline_for(top + side / 2, style, "label"), name, "label", style["neutral"]["ink"]),
                      "part": "name"})
    return cells + values + names
