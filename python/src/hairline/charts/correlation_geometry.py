"""Correlation heatmap geometry in pt: the lower triangle without the diagonal, each variable named on the empty
diagonal (one label serves its row and its column), values printed in the cells. Pure, like the donut geometry."""

from __future__ import annotations

from hairline.charts.donut_geometry import Measure, baseline_for, line_height, text
from hairline.charts.tips import tagged
from hairline.charts.wrapping import TOLERANCE, fit_lines, widest_line
from hairline.color.vision import contrast
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens


def least_cell(spec: dict, measure: Measure, rules: dict) -> float:
    """The smallest cell that holds its value: the widest value and the cell's gap on either side (same in R)."""
    count = len(spec["names"])
    widest = max(measure(spec["texts"][row][column], "label") for row in range(count) for column in range(row))
    return widest + 2 * rules["gap_pt"]


def shows_values(spec: dict, box: Box, measure: Measure, style: dict, rules: dict) -> bool:
    """Values print in the cells while cells that hold them leave the names room for their widest word; otherwise
    the cells keep only their colour, which the key reads (same rule in R)."""
    count = len(spec["names"])
    room = box.width - count * least_cell(spec, measure, rules) - rules["label_gap"] * style["base"]
    return room + TOLERANCE >= max(measure(word, "label") for name in spec["names"] for word in name.split())


def name_lines(spec: dict, box: Box, measure: Measure, style: dict, rules: dict, values: bool) -> list[list[str]]:
    """Each name on one line while the cells keep their least size (room for a value, or a line of text without
    one); otherwise wrapped into the width that leaves, and a word wider than that is refused with the room it
    needs (the rule of every chart's labels)."""
    count = len(spec["names"])
    least = least_cell(spec, measure, rules) if values else line_height(style, "label") + 2 * rules["gap_pt"]
    room = box.width - count * least - rules["label_gap"] * style["base"]
    return [fit_lines(name, room, measure, "correlation", "the name") for name in spec["names"]]


def cell_side(spec: dict, box: Box, measure: Measure, style: dict, rules: dict, lines: list[list[str]]) -> float:
    """Square cells, as large as the box allows beside the names but at most `max_cell` times the base size, and
    never lower than a name's lines."""
    count = len(spec["names"])
    widest = max(widest_line(name, measure) for name in lines)
    side = min(rules["max_cell"] * style["base"], box.height / count,
               (box.width - widest - rules["label_gap"] * style["base"]) / count)
    tallest = max(len(name) for name in lines) * line_height(style, "label")
    return max(side, tallest)


def text_color(fill: str, style: dict) -> str:
    neutral = style["neutral"]
    dark = contrast(fill, neutral["ink"]) >= contrast(fill, neutral["surface"])
    return neutral["ink"] if dark else neutral["surface"]


def correlation_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    rules = load_tokens()["correlation"]
    values_shown = shows_values(spec, box, measure, style, rules)
    lines = name_lines(spec, box, measure, style, rules, values_shown)
    side, inset = cell_side(spec, box, measure, style, rules, lines), rules["gap_pt"] / 2
    cells, values, names = [], [], []
    for row, name in enumerate(spec["names"]):
        top = box.y + row * side
        for column in range(row):
            left, fill = box.x + column * side, spec["colors"][row][column]
            pair = f"{name} \u00d7 {spec['names'][column]}"
            cells.append(tagged({"kind": "polygon", "role": "cell", "fill": fill,
                                 "points": [[left + inset, top + inset], [left + side - inset, top + inset],
                                            [left + side - inset, top + side - inset],
                                            [left + inset, top + side - inset]]},
                                pair, f"{pair}: {spec['texts'][row][column]}"))
            if not values_shown:
                continue
            values.append({**text(left + side / 2, baseline_for(top + side / 2, style, "label"),
                                  spec["texts"][row][column], "label", text_color(fill, style), "center"),
                           "part": "value"})
        first = top + side / 2 - (len(lines[row]) - 1) * line_height(style, "label") / 2
        names += [{**text(box.x + row * side + rules["label_gap"] * style["base"],
                          baseline_for(first + index * line_height(style, "label"), style, "label"), line, "label",
                          style["neutral"]["ink"]), "part": "name"} for index, line in enumerate(lines[row])]
    return cells + values + names
