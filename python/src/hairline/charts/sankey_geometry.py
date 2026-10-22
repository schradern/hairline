"""Sankey geometry in pt: nodes stacked on one scale, later columns ordered by the barycentre of their sources,
links ordered at both ends by the node at the other end, labels outside the outer columns and above the middle
nodes on a surface halo. Labels wrap when the links would keep less than `min_plot`; the gap between nodes holds the
tallest label, and a column with more nodes than the panel holds runs on below it. Pure, like the donut geometry."""

from __future__ import annotations

from hairline.charts.donut_geometry import Measure, baseline_for, label_pair, line_height, text
from hairline.charts.tips import amount_text, tagged
from hairline.charts.wrapping import fit_lines, pair_width
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
            pair = f"{link['source']} \u2192 {link['target']}"
            shapes.append(tagged({"kind": "polygon", "points": outline, "fill": link["color"],
                                  "alpha": rules["link_opacity"], "role": "link", "column": index,
                                  "source": link["source"], "target": link["target"]},
                                 pair, f"{pair}: {amount_text(link['value'])}"))
    return shapes


def node_shapes(ordered: list[list[dict]], positions: list[dict], xs: list[float], width: float) -> list[dict]:
    shapes = []
    for nodes, places, x in zip(ordered, positions, xs, strict=True):
        for node in nodes:
            top, bottom = places[node["name"]]
            shapes.append(tagged({"kind": "polygon", "points": [[x, top], [x + width, top], [x + width, bottom],
                                                                 [x, bottom]],
                                  "fill": node["color"], "role": "node", "name": node["name"]},
                                 node["name"], f"{node['name']}: {node['value_text']}"))
    return shapes


def as_segment(node: dict) -> dict:
    return {"name": node["name"], "share_text": node["value_text"]}


def label_space(style: dict) -> float:
    return load_tokens()["donut"]["label_space"] * style["sizes"]["label"]


def node_lines(nodes: list[dict], room: float, measure: Measure, style: dict) -> dict[str, list[str]]:
    """Each node's name in lines no wider than `room`, its value following the last."""
    return {node["name"]: fit_lines(node["name"], room, measure, "sankey", "the label",
                                    measure(node["value_text"], "label"), label_space(style)) for node in nodes}


def block_width(node: dict, lines: list[str], measure: Measure, style: dict) -> float:
    return pair_width(lines, measure, measure(node["value_text"], "label"), label_space(style))


def outer_rooms(left: float, right: float, room: float) -> tuple[float, float]:
    """Widths of the two outer label columns: their labels' widths while both fit `room`; otherwise a column
    narrower than half keeps its width and the other takes the rest, or each takes half."""
    if left + right <= room:
        return left, right
    if left <= room / 2:
        return left, room - left
    if right <= room / 2:
        return room - right, right
    return room / 2, room / 2


def middle_label(node: dict, lines: list[str], top: float, centre: float, measure: Measure, style: dict,
                 rules: dict) -> list[dict]:
    """Name and value centred above the node, on a surface halo so links behind stay quiet; a wrapped name stacks
    its lines upwards from the node, the value after the last."""
    size, base, neutral, line = style["sizes"]["label"], style["base"], style["neutral"], line_height(style, "label")
    space, value = label_space(style), measure(node["value_text"], "label")
    widths = [measure(content, "label") for content in lines]
    widths[-1] = widths[-1] + space + value if lines[-1] else value
    baseline = top - rules["label_pad"] * base - style["descender"] * size
    first, pad, half = baseline - (len(lines) - 1) * line, rules["halo_pad"] * base, max(widths) / 2
    upper, lower = first - style["cap_height"] * size - pad, baseline + style["descender"] * size + pad
    shapes = [{"kind": "polygon", "points": [[centre - half - pad, upper], [centre + half + pad, upper],
                                             [centre + half + pad, lower], [centre - half - pad, lower]],
               "fill": neutral["surface"], "role": "halo"}]
    shapes += [text(centre - width / 2, first + index * line, content, "label", neutral["ink"])
               for index, (content, width) in enumerate(zip(lines, widths, strict=True)) if content]
    return shapes + [text(centre - widths[-1] / 2 + widths[-1] - value, baseline, node["value_text"], "label",
                          neutral["muted"])]


def label_shapes(ordered: list[list[dict]], positions: list[dict], xs: list[float], width: float, measure: Measure,
                 style: dict, rules: dict, lines: list[dict[str, list[str]]]) -> list[dict]:
    shapes, gap, donut = [], rules["label_gap"] * style["base"], load_tokens()["donut"]
    line = line_height(style, "label")
    for index, (nodes, places, x) in enumerate(zip(ordered, positions, xs, strict=True)):
        for node in nodes:
            top, bottom = places[node["name"]]
            name = lines[index][node["name"]]
            first = (top + bottom) / 2 - (len(name) - 1) * line / 2
            if index == 0:
                shapes += label_pair(as_segment(node), x - gap, first, "left", measure, style, donut, name)
            elif index == len(ordered) - 1:
                shapes += label_pair(as_segment(node), x + width + gap, first, "right", measure, style, donut, name)
            else:
                shapes += middle_label(node, name, top, x + width / 2, measure, style, rules)
    return shapes


def heading_shapes(headings: list[str], xs: list[float], width: float, baseline: float, style: dict) -> list[dict]:
    last, muted = len(xs) - 1, style["neutral"]["muted"]
    return [text(x + width if index == 0 else x if index == last else x + width / 2, baseline, heading, "label", muted,
                 "right" if index == 0 else "left" if index == last else "center")
            for index, (heading, x) in enumerate(zip(headings, xs, strict=True))]


def outer_width(nodes: list[dict], measure: Measure, style: dict, rules: dict) -> float:
    space = load_tokens()["donut"]["label_space"] * style["sizes"]["label"]
    widest = max(measure(node["name"], "label") + space + measure(node["value_text"], "label") for node in nodes)
    return widest + rules["label_gap"] * style["base"]


def column_lines(spec: dict, box: Box, width: float, measure: Measure, style: dict,
                 rules: dict) -> tuple[list[dict[str, list[str]]], list[float]]:
    """Every node's label lines and the x of each column: the outer labels share what the links leave them at
    `min_plot`, the middle labels the space between columns."""
    nodes, count, gap = spec["nodes"], len(spec["nodes"]), rules["label_gap"] * style["base"]
    rooms = outer_rooms(outer_width(nodes[0], measure, style, rules), outer_width(nodes[-1], measure, style, rules),
                        box.width - width - rules["min_plot"] * style["base"])
    outer = [node_lines(nodes[0], rooms[0] - gap, measure, style), node_lines(nodes[-1], rooms[1] - gap, measure,
                                                                              style)]
    left, right = (max(block_width(node, lines[node["name"]], measure, style) for node in column) + gap
                   for column, lines in zip((nodes[0], nodes[-1]), outer, strict=True))
    first, last = box.x + left, box.x + box.width - right - width
    xs = [first + (last - first) * index / (count - 1) for index in range(count)]
    middle = [node_lines(column, (last - first) / (count - 1) - 2 * gap, measure, style) for column in nodes[1:-1]]
    return [outer[0], *middle, outer[1]], xs


def sankey_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    """Every shape of one Sankey diagram inside `box` (pt from the figure's top-left corner)."""
    rules, base, count = load_tokens()["sankey"], style["base"], len(spec["nodes"])
    line, width = line_height(style, "label"), rules["node_width"] * base
    lines, xs = column_lines(spec, box, width, measure, style, rules)
    tallest = max(len(name) for column in lines for name in column.values())
    raised = max((len(name) for column in lines[1:-1] for name in column.values()), default=0)
    gap = tallest * line + rules["node_gap"] * base
    top = box.y + line + rules["heading_gap"] * base + raised * line
    most = max(len(column) for column in spec["nodes"])
    height = max(box.y + box.height - top, (most - 1) * gap + most * line)
    ordered, positions, scale = place_nodes(spec, top, height, gap)
    return (link_shapes(spec, positions, xs, width, scale, rules) + node_shapes(ordered, positions, xs, width)
            + label_shapes(ordered, positions, xs, width, measure, style, rules, lines)
            + heading_shapes(spec["headings"], xs, width, baseline_for(box.y + line / 2, style, "label"), style))
