"""Arc diagram geometry in pt: nodes evenly spaced on a baseline, half-ellipse arcs above whose width follows the
value, labels under the nodes (turned upright when they would collide), a width key at the top. Pure."""

from __future__ import annotations

import math

from hairline.charts.donut_geometry import Measure, baseline_for, line_height, text
from hairline.charts.tips import tagged
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens


def stroke(value: float, largest: float, style: dict, rules: dict) -> float:
    base = style["base"]
    return rules["min_width"] * base + (rules["max_width"] - rules["min_width"]) * base * value / largest


def node_positions(names: list[str], box: Box, measure: Measure) -> list[float]:
    first, last = measure(names[0], "label") / 2, measure(names[-1], "label") / 2
    span = box.width - first - last
    return [box.x + first + span * index / max(len(names) - 1, 1) for index in range(len(names))]


def crowded(names: list[str], xs: list[float], measure: Measure, gap: float) -> bool:
    return any(measure(a, "label") / 2 + measure(b, "label") / 2 + gap > x2 - x1
               for a, b, x1, x2 in zip(names, names[1:], xs, xs[1:], strict=False))


def label_shapes(names: list[str], xs: list[float], baseline_y: float, measure: Measure, style: dict,
                 rules: dict) -> tuple[list[dict], float]:
    """Labels under the nodes and the height they take; upright (rotated) when side by side would collide."""
    gap, ink = rules["label_gap"] * style["base"], style["neutral"]["ink"]
    if not crowded(names, xs, measure, gap):
        line = line_height(style, "label")
        return [{**text(x, baseline_y - style["descender"] * style["sizes"]["label"], name, "label", ink, "center"),
                 "part": "node"} for name, x in zip(names, xs, strict=True)], line
    tallest = max(measure(name, "label") for name in names)
    top = baseline_y - tallest
    shift = style["cap_height"] * style["sizes"]["label"] / 2
    return [{**text(x + shift, top, name, "label", ink, "right"), "rotation": 90, "part": "node"}
            for name, x in zip(names, xs, strict=True)], tallest


def key_shapes(spec: dict, box: Box, largest: float, measure: Measure, style: dict, rules: dict) -> list[dict]:
    base, baseline = style["base"], baseline_for(box.y + line_height(style, "label") / 2, style, "label")
    x, shapes, muted = box.x, [], style["neutral"]["muted"]
    for item in spec["key"]:
        middle = box.y + line_height(style, "label") / 2
        shapes.append({"kind": "line", "points": [[x, middle], [x + rules["key_line"] * base, middle]],
                       "color": spec["color"], "width": stroke(item["value"], largest, style, rules),
                       "alpha": rules["opacity"], "part": "key"})
        x += rules["key_line"] * base + style["swatch_text"] * base
        shapes.append({**text(x, baseline, item["text"], "label", muted), "part": "key"})
        x += measure(item["text"], "label") + rules["key_gap"] * base
    return shapes


def arc_points(start: float, end: float, ground: float, height: float, count: int) -> list[list[float]]:
    centre, radius = (start + end) / 2, abs(end - start) / 2
    return [[centre - radius * math.cos(math.pi * step / count), ground - height * math.sin(math.pi * step / count)]
            for step in range(count + 1)]


def arcs_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    rules, base = load_tokens()["arcs"], style["base"]
    names, largest = spec["nodes"], max(link["value"] for link in spec["links"])
    xs = node_positions(names, box, measure)
    labels, label_height = label_shapes(names, xs, box.y + box.height, measure, style, rules)
    ground = box.y + box.height - label_height - rules["label_gap"] * base
    ceiling = box.y + line_height(style, "label") + rules["key_gap"] * base
    position = dict(zip(names, xs, strict=True))
    widest = max(abs(position[link["target"]] - position[link["source"]]) / 2 for link in spec["links"])
    squeeze = min(1.0, (ground - ceiling) / widest)
    shapes = []
    for link in sorted(spec["links"], key=lambda item: -item["value"]):
        start, end = position[link["source"]], position[link["target"]]
        pair = f"{link['source']} \u2192 {link['target']}"
        shapes.append(tagged({"kind": "line", "points": arc_points(start, end, ground,
                                                                   abs(end - start) / 2 * squeeze, rules["points"]),
                              "color": spec["color"], "width": stroke(link["value"], largest, style, rules),
                              "alpha": rules["opacity"], "role": "arc", "source": link["source"],
                              "target": link["target"]},
                             pair, f"{pair}: {link['value_text']}"))
    radius = rules["node_radius"] * base
    for x in xs:
        shapes.append({"kind": "polygon", "role": "node_dot", "fill": style["neutral"]["ink"],
                       "points": [[x + radius * math.cos(2 * math.pi * step / 24),
                                   ground + radius * math.sin(2 * math.pi * step / 24)] for step in range(24)]})
    return shapes + labels + key_shapes(spec, box, largest, measure, style, rules)
