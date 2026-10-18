"""Chord diagram geometry in pt: groups as arcs on a ring sized by their total, ribbons through the centre joining
each pair with the pair's value at both ends, labels outside with leader lines (as on the donut). Pure."""

from __future__ import annotations

from hairline.charts.donut_geometry import Measure, arc, line_height, outside_labels, outside_width
from hairline.charts.tips import amount_text, tagged
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens


def node_spans(spec: dict, rules: dict) -> list[tuple[float, float]]:
    """Clockwise from the top, each group's share of 360 degrees less the gaps between groups."""
    total = sum(node["value"] for node in spec["nodes"])
    available = 360 - rules["gap_degrees"] * len(spec["nodes"])
    spans, start = [], 90.0 - rules["gap_degrees"] / 2
    for node in spec["nodes"]:
        end = start - available * node["value"] / total
        spans.append((start, end))
        start = end - rules["gap_degrees"]
    return spans


def partner_order(item: tuple[int, dict], names: list[str], index: int) -> tuple[int, int]:
    """Partners clockwise from this group, then input order."""
    position, link = item
    other = link["target"] if link["source"] == names[index] else link["source"]
    return ((names.index(other) - index) % len(names), position)


def link_ends(spec: dict, spans: list[tuple[float, float]]) -> dict[tuple[int, int], tuple[float, float]]:
    """Angles of each link at each of its two groups; at a group, links run in the order of their partners."""
    names = [node["name"] for node in spec["nodes"]]
    ends = {}
    for index, node in enumerate(spec["nodes"]):
        touching = [(position, link) for position, link in enumerate(spec["links"])
                    if names[index] in (link["source"], link["target"])]
        start, end = spans[index]
        cursor = start
        for position, link in sorted(touching, key=lambda item, here=index: partner_order(item, names, here)):
            width = (start - end) * link["value"] / node["value"]
            ends[(position, index)] = (cursor, cursor - width)
            cursor -= width
    return ends


def bend(start: list[float], end: list[float], centre: tuple[float, float], count: int) -> list[list[float]]:
    """Quadratic curve from start to end pulled through the centre."""
    return [[(1 - t) ** 2 * start[0] + 2 * (1 - t) * t * centre[0] + t ** 2 * end[0],
             (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * centre[1] + t ** 2 * end[1]]
            for t in (step / count for step in range(1, count))]


def ribbon(first: tuple[float, float], second: tuple[float, float], cx: float, cy: float, radius: float,
           step: float) -> list[list[float]]:
    one, two = arc(cx, cy, radius, *first, step), arc(cx, cy, radius, *second, step)
    return one + bend(one[-1], two[0], (cx, cy), 16) + two + bend(two[-1], one[0], (cx, cy), 16)


def chord_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    rules, donut = load_tokens()["chord"], load_tokens()["donut"]
    segments = [{"name": node["name"], "share_text": node["value_text"]} for node in spec["nodes"]]
    side = outside_width(segments, measure, style, donut)
    radius = max(min(box.height / 2 - line_height(style, "label") / 2, (box.width - 2 * side) / 2),
                 donut["min_radius"] * style["base"])
    cx, cy = box.x + box.width / 2, box.y + box.height / 2
    inner = radius * (1 - rules["ring"])
    spans = node_spans(spec, rules)
    ends = link_ends(spec, spans)
    names = [node["name"] for node in spec["nodes"]]
    shapes = []
    for position, link in enumerate(spec["links"]):
        first, second = names.index(link["source"]), names.index(link["target"])
        pair = f"{link['source']} \u2013 {link['target']}"
        shapes.append(tagged({"kind": "polygon", "role": "ribbon", "fill": spec["nodes"][first]["color"],
                              "alpha": rules["ribbon_opacity"],
                              "points": ribbon(ends[(position, first)], ends[(position, second)], cx, cy,
                                               inner - rules["ribbon_gap"], rules["arc_step"])},
                             pair, f"{pair}: {amount_text(link['value'])}"))
    for node, (start, end) in zip(spec["nodes"], spans, strict=True):
        outline = arc(cx, cy, radius, start, end, rules["arc_step"]) + arc(cx, cy, inner, end, start,
                                                                          rules["arc_step"])
        shapes.append(tagged({"kind": "polygon", "role": "node", "name": node["name"], "span": start - end,
                              "fill": node["color"], "points": outline},
                             node["name"], f"{node['name']}: {node['value_text']}"))
    return shapes + outside_labels(segments, cx, cy, radius, box, measure, style, donut, spans)

