"""Sankey geometry in pt: nodes stacked on one scale, later columns ordered by the barycentre of their sources,
links ordered at both ends by the node at the other end, labels outside the outer columns and above the middle
nodes on a surface halo. Pure, like the donut geometry."""

from __future__ import annotations

from hairline.charts.donut_geometry import Measure, baseline_for, label_pair, line_height, text
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens


def barycentre_order(nodes: list[dict], links: list[dict], previous: dict[str, tuple[float, float]]) -> list[dict]:
    """Nodes sorted by the value-weighted centre of their sources (rounded, so exact ties keep the given order);
    nodes without sources go last."""
    def key(item: tuple[int, dict]) -> tuple[float, int]:
        index, node = item
        incoming = [link for link in links if link["target"] == node["name"]]
        total = sum(link["value"] for link in incoming)
        if not total:
            return float("inf"), index
        centre = sum(link["value"] * (previous[link["source"]][0] + previous[link["source"]][1]) / 2
                     for link in incoming) / total
        return round(centre, 6), index
    return [node for _, node in sorted(enumerate(nodes), key=key)]


def stack(nodes: list[dict], top: float, height: float, scale: float, gap: float) -> dict[str, tuple[float, float]]:
    used = sum(node["value"] for node in nodes) * scale + gap * (len(nodes) - 1)
    y, positions = top + (height - used) / 2, {}
    for node in nodes:
        positions[node["name"]] = (y, y + node["value"] * scale)
        y += node["value"] * scale + gap
    return positions


def place_nodes(spec: dict, top: float, height: float, gap: float) -> tuple[list[list[dict]], list[dict], float]:
    columns = spec["nodes"]
    scale = min((height - gap * (len(nodes) - 1)) / sum(node["value"] for node in nodes) for nodes in columns)
    ordered, positions = [columns[0]], [stack(columns[0], top, height, scale, gap)]
    for index in range(1, len(columns)):
        links = [link for link in spec["links"] if link["column"] == index - 1]
        ordered.append(barycentre_order(columns[index], links, positions[-1]))
        positions.append(stack(ordered[-1], top, height, scale, gap))
    return ordered, positions, scale


def bezier(start: list[float], end: list[float], count: int) -> list[list[float]]:
    middle = (start[0] + end[0]) / 2
    points = []
    for step in range(count + 1):
        t = step / count
        x = (1 - t) ** 3 * start[0] + 3 * (1 - t) ** 2 * t * middle + 3 * (1 - t) * t ** 2 * middle + t ** 3 * end[0]
        y = ((1 - t) ** 3 + 3 * (1 - t) ** 2 * t) * start[1] + (3 * (1 - t) * t ** 2 + t ** 3) * end[1]
        points.append([x, y])
    return points


def link_offsets(links: list[dict], end: str, other: str, positions: dict, groups: list[str], scale: float) -> dict:
    """Top of every link at one end: per node, links stacked in the order of the node at their other end."""
    offsets, filled = {}, {}
    for link in sorted(links, key=lambda item: (positions[1][item[other]][0], groups.index(item["group"]))):
        start = filled.get(link[end], positions[0][link[end]][0])
        offsets[id(link)] = start
        filled[link[end]] = start + link["value"] * scale
    return offsets


def link_shapes(spec: dict, positions: list[dict], xs: list[float], width: float, scale: float,
                rules: dict) -> list[dict]:
    shapes, groups = [], spec["groups"]
    for index in range(len(positions) - 1):
        links = [link for link in spec["links"] if link["column"] == index]
        here, there = positions[index], positions[index + 1]
        tops = link_offsets(links, "source", "target", (here, there), groups, scale)
        ends = link_offsets(links, "target", "source", (there, here), groups, scale)
        start_x, end_x = xs[index] + width, xs[index + 1]
        for link in links:
            thickness, top, end = link["value"] * scale, tops[id(link)], ends[id(link)]
            outline = bezier([start_x, top], [end_x, end], rules["curve_points"]) + bezier(
                [end_x, end + thickness], [start_x, top + thickness], rules["curve_points"])
            shapes.append({"kind": "polygon", "points": outline, "fill": link["color"], "alpha": rules["link_opacity"],
                           "role": "link", "column": index, "source": link["source"], "target": link["target"]})
    return shapes


def node_shapes(ordered: list[list[dict]], positions: list[dict], xs: list[float], width: float) -> list[dict]:
    shapes = []
    for nodes, places, x in zip(ordered, positions, xs, strict=True):
        for node in nodes:
            top, bottom = places[node["name"]]
            shapes.append({"kind": "polygon", "points": [[x, top], [x + width, top], [x + width, bottom], [x, bottom]],
                           "fill": node["color"], "role": "node", "name": node["name"]})
    return shapes


def as_segment(node: dict) -> dict:
    return {"name": node["name"], "share_text": node["value_text"]}


def middle_label(node: dict, top: float, centre: float, measure: Measure, style: dict, rules: dict) -> list[dict]:
    """Name and value centred above the node, on a surface halo so links behind stay quiet."""
    size, base, neutral = style["sizes"]["label"], style["base"], style["neutral"]
    space = load_tokens()["donut"]["label_space"] * size
    name, value = measure(node["name"], "label"), measure(node["value_text"], "label")
    start, baseline = centre - (name + space + value) / 2, top - rules["label_pad"] * base - style["descender"] * size
    pad, end = rules["halo_pad"] * base, centre + (name + space + value) / 2
    upper, lower = baseline - style["cap_height"] * size - pad, baseline + style["descender"] * size + pad
    return [{"kind": "polygon", "points": [[start - pad, upper], [end + pad, upper], [end + pad, lower],
                                           [start - pad, lower]], "fill": neutral["surface"], "role": "halo"},
            text(start, baseline, node["name"], "label", neutral["ink"]),
            text(start + name + space, baseline, node["value_text"], "label", neutral["muted"])]


def label_shapes(ordered: list[list[dict]], positions: list[dict], xs: list[float], width: float, measure: Measure,
                 style: dict, rules: dict) -> list[dict]:
    shapes, gap, donut = [], rules["label_gap"] * style["base"], load_tokens()["donut"]
    for index, (nodes, places, x) in enumerate(zip(ordered, positions, xs, strict=True)):
        for node in nodes:
            top, bottom = places[node["name"]]
            if index == 0:
                shapes += label_pair(as_segment(node), x - gap, (top + bottom) / 2, "left", measure, style, donut)
            elif index == len(ordered) - 1:
                shapes += label_pair(as_segment(node), x + width + gap, (top + bottom) / 2, "right", measure, style,
                                     donut)
            else:
                shapes += middle_label(node, top, x + width / 2, measure, style, rules)
    return shapes


def heading_shapes(headings: list[str], xs: list[float], width: float, baseline: float, style: dict) -> list[dict]:
    last, ink = len(xs) - 1, style["neutral"]["ink"]
    return [text(x + width if index == 0 else x if index == last else x + width / 2, baseline, heading, "panel", ink,
                 "right" if index == 0 else "left" if index == last else "center")
            for index, (heading, x) in enumerate(zip(headings, xs, strict=True))]


def outer_width(nodes: list[dict], measure: Measure, style: dict, rules: dict) -> float:
    space = load_tokens()["donut"]["label_space"] * style["sizes"]["label"]
    widest = max(measure(node["name"], "label") + space + measure(node["value_text"], "label") for node in nodes)
    return widest + rules["label_gap"] * style["base"]


def sankey_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    """Every shape of one Sankey diagram inside `box` (pt from the figure's top-left corner)."""
    rules, base, count = load_tokens()["sankey"], style["base"], len(spec["nodes"])
    line, width = line_height(style, "label"), rules["node_width"] * base
    first = box.x + outer_width(spec["nodes"][0], measure, style, rules)
    last = box.x + box.width - outer_width(spec["nodes"][-1], measure, style, rules) - width
    xs = [first + (last - first) * index / (count - 1) for index in range(count)]
    top = box.y + line_height(style, "panel") + rules["heading_gap"] * base + (line if count > 2 else 0.0)
    ordered, positions, scale = place_nodes(spec, top, box.y + box.height - top, line + rules["node_gap"] * base)
    return (link_shapes(spec, positions, xs, width, scale, rules) + node_shapes(ordered, positions, xs, width)
            + label_shapes(ordered, positions, xs, width, measure, style, rules)
            + heading_shapes(spec["headings"], xs, width, baseline_for(box.y + line_height(style, "panel") / 2,
                                                                         style, "panel"), style))
