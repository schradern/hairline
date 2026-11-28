"""Flows of a process diagram in pt: a flow within a stage runs straight up or down between the steps' facing
edges; a flow to a later stage leaves its step's right edge and enters the target's left edge, turning in the gap
before the target (or, when a step blocks its own lane, in the gap after the source), with rounded corners and a
small filled head. Its label sits above where it leaves. Pure; mirrored in R's process_routes.R."""

from __future__ import annotations

import math

from hairline.charts.donut_geometry import Measure, text


def corner(before: list[float], vertex: list[float], after: list[float], radius: float,
           steps: int) -> list[list[float]]:
    """A corner rounded as a quadratic curve from `radius` before the vertex to `radius` after it."""
    room = min(radius, math.dist(before, vertex) / 2, math.dist(vertex, after) / 2)
    if room <= 0:
        return [vertex]
    start = [vertex[axis] + room * (before[axis] - vertex[axis]) / math.dist(before, vertex) for axis in (0, 1)]
    end = [vertex[axis] + room * (after[axis] - vertex[axis]) / math.dist(vertex, after) for axis in (0, 1)]
    return [[(1 - t) ** 2 * start[axis] + 2 * (1 - t) * t * vertex[axis] + t ** 2 * end[axis] for axis in (0, 1)]
            for t in (step / steps for step in range(steps + 1))]


def rounded(points: list[list[float]], radius: float, steps: int) -> list[list[float]]:
    inner = [corner(points[index - 1], points[index], points[index + 1], radius, steps)
             for index in range(1, len(points) - 1)]
    return [points[0], *(point for curve in inner for point in curve), points[-1]]


def head(points: list[list[float]], size: float) -> tuple[list[list[float]], list[list[float]]]:
    """The path stopped short by the head's length, and the head: a triangle pointing along the last segment."""
    end, before = points[-1], points[-2]
    length = math.dist(before, end)
    along = [(end[0] - before[0]) / length, (end[1] - before[1]) / length]
    base = [end[0] - size * along[0], end[1] - size * along[1]]
    across = [-along[1] * size / 2, along[0] * size / 2]
    return points[:-1] + [base], [end, [base[0] + across[0], base[1] + across[1]],
                                  [base[0] - across[0], base[1] - across[1]]]


def free(cells: set, lane: int, stages: range) -> bool:
    return all((lane, stage) not in cells for stage in stages)


def route_kind(source: dict, target: dict, cells: set, where: str) -> str:
    """How a flow runs between two steps (their lane and stage) without crossing another step: 'vertical' within a
    stage, 'straight' along a lane, turning 'before' the target or 'after' the source; a ValueError when every way
    crosses a step."""
    if source["stage"] == target["stage"]:
        lanes = range(min(source["lane"], target["lane"]) + 1, max(source["lane"], target["lane"]))
        kind = "vertical" if all((lane, source["stage"]) not in cells for lane in lanes) else None
    else:
        between = range(source["stage"] + 1, target["stage"])
        if source["lane"] == target["lane"]:
            kind = "straight" if free(cells, source["lane"], between) else None
        elif free(cells, source["lane"], between):
            kind = "before"
        else:
            kind = "after" if free(cells, target["lane"], between) else None
    if kind is None:
        raise ValueError(f"hairline: process: the flow from {source['name']!r} to {target['name']!r} would cross "
                         f"another step{where}; move one of them to another stage or lane")
    return kind


def path(source: dict, target: dict, cells: set, turns: list[float], where: str) -> list[list[float]]:
    """The corner points of a flow from step `source` to step `target` (their boxes and cells)."""
    kind = route_kind(source, target, cells, where)
    if kind == "vertical":
        down = target["lane"] > source["lane"]
        return [[source["cx"], source["bottom"] if down else source["top"]],
                [target["cx"], target["top"] if down else target["bottom"]]]
    if kind == "straight":
        return [[source["right"], source["cy"]], [target["left"], target["cy"]]]
    turn = turns[target["stage"] - 1] if kind == "before" else turns[source["stage"]]
    return [[source["right"], source["cy"]], [turn, source["cy"]], [turn, target["cy"]],
            [target["left"], target["cy"]]]


def flow_label(flow: dict, source: dict, target: dict, measure: Measure, style: dict, rules: dict,
               offset: float) -> list[dict]:
    """The flow's label in muted text on a surface halo, so a line or rule behind it stays quiet: above where it
    leaves its step, or right of a flow within a stage."""
    if not flow["label"]:
        return []
    base, size = style["base"], style["sizes"]["label"]
    pad, halo = rules["label_pad"] * base, rules["halo_pad"] * base
    if source["stage"] == target["stage"]:
        low, high = sorted((source["bottom"], target["top"]) if target["lane"] > source["lane"]
                           else (target["bottom"], source["top"]))
        x, y = source["cx"] + pad, (low + high) / 2 + style["cap_height"] * size / 2
    else:
        x, y = source["right"] + pad + offset, source["cy"] - pad - style["descender"] * size
    left, right = x - halo, x + measure(flow["label"], "label") + halo
    upper, lower = y - style["cap_height"] * size - halo, y + style["descender"] * size + halo
    return [{"kind": "polygon", "points": [[left, upper], [right, upper], [right, lower], [left, lower]],
             "fill": style["neutral"]["surface"], "role": "halo"},
            {**text(x, y, flow["label"], "label", style["neutral"]["muted"]), "part": "flow_label"}]


def flow_shapes(flow: dict, places: list[dict], cells: set, turns: list[float], style: dict, rules: dict,
                accent: str, where: str) -> list[dict]:
    """A flow's line and head: faint, in the accent and thicker when highlighted, dashed when tentative."""
    source, target = places[flow["source"]], places[flow["target"]]
    base = style["base"]
    points = rounded(path(source, target, cells, turns, where), rules["corner"] * base, rules["corner_steps"])
    line, tip = head(points, rules["arrow_head"] * base)
    color = accent if flow["status"] == "highlight" else style["neutral"]["faint"]
    width = rules["highlight_width"] * base if flow["status"] == "highlight" else style["leader_width"]
    stroke = {"kind": "line", "points": line, "color": color, "width": width, "role": "flow"}
    if flow["status"] == "tentative":
        stroke["dash"] = list(rules["dash"])
    return [stroke, {"kind": "polygon", "points": tip, "fill": color, "role": "flow_head"}]
