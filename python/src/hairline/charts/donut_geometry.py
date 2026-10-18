"""Donut geometry in pt: segment outlines with constant-width gaps, outside labels with leader lines,
labels along the rings, the centre total and the hierarchical key. Pure: the same inputs give the same
shapes in both languages; `measure(text, role)` supplies text widths."""

from __future__ import annotations

import math
from collections.abc import Callable

from hairline.charts.labels import spread_labels
from hairline.color.vision import contrast
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens

Measure = Callable[..., float]


def point(cx: float, cy: float, radius: float, angle: float) -> list[float]:
    return [cx + radius * math.cos(math.radians(angle)), cy - radius * math.sin(math.radians(angle))]


def arc(cx: float, cy: float, radius: float, start: float, end: float, step: float) -> list[list[float]]:
    count = max(2, math.ceil(abs(start - end) / step) + 1)
    return [point(cx, cy, radius, start + (end - start) * index / (count - 1)) for index in range(count)]


def segment_polygon(cx: float, cy: float, inner: float, outer: float, span: tuple[float, float],
                    rules: dict) -> list[list[float]] | None:
    """Annulus sector from span[0] down to span[1] (degrees, clockwise), inset so neighbours keep a fixed gap."""
    gap, step = rules["gap_pt"], rules["arc_step"]
    inset_outer = math.degrees(math.asin(min(1.0, gap / 2 / outer)))
    inset_inner = math.degrees(math.asin(min(1.0, gap / 2 / inner)))
    start, end = span
    if start - end <= 2 * inset_inner:
        return None
    return arc(cx, cy, outer, start - inset_outer, end + inset_outer, step) + arc(
        cx, cy, inner, end + inset_inner, start - inset_inner, step)


def ring_radii(count: int, radius: float, hole: float, gap: float) -> list[tuple[float, float]]:
    start = hole * radius
    thickness = (radius - start - gap * (count - 1)) / count
    return [(start + ring * (thickness + gap), start + ring * (thickness + gap) + thickness) for ring in range(count)]


def ring_spans(ring: list[dict]) -> list[tuple[float, float]]:
    spans, cumulative = [], 0.0
    for segment in ring:
        spans.append((90 - 360 * cumulative, 90 - 360 * (cumulative + segment["share"])))
        cumulative += segment["share"]
    return spans


def segment_shapes(rings: list[list[dict]], cx: float, cy: float, radii: list[tuple[float, float]],
                   rules: dict) -> list[dict]:
    shapes = []
    for ring, (inner, outer) in zip(rings, radii, strict=True):
        for segment, span in zip(ring, ring_spans(ring), strict=True):
            points = segment_polygon(cx, cy, inner, outer, span, rules)
            if points:
                shapes.append({"kind": "polygon", "points": points, "fill": segment["color"]})
    return shapes


def text(x: float, y: float, content: str, role: str, color: str, align: str = "left",
         weight: int | None = None) -> dict:
    return {"kind": "text", "x": x, "y": y, "text": content, "role": role, "color": color, "align": align,
            "weight": weight}


def line_height(style: dict, role: str) -> float:
    return style["sizes"][role] * (1 + style["line_gap"])


def baseline_for(centre: float, style: dict, role: str) -> float:
    return centre + style["cap_height"] * style["sizes"][role] / 2


def label_pair(segment: dict, x: float, y: float, side: str, measure: Measure, style: dict, rules: dict) -> list:
    """Name in ink, share in muted, reading left to right, aligned away from the donut."""
    size, neutral = style["sizes"]["label"], style["neutral"]
    space, baseline = rules["label_space"] * size, baseline_for(y, style, "label")
    if side == "right":
        name_width = measure(segment["name"], "label")
        return [text(x, baseline, segment["name"], "label", neutral["ink"]),
                text(x + name_width + space, baseline, segment["share_text"], "label", neutral["muted"])]
    share_width = measure(segment["share_text"], "label")
    return [text(x - share_width - space, baseline, segment["name"], "label", neutral["ink"], "right"),
            text(x, baseline, segment["share_text"], "label", neutral["muted"], "right")]


def outside_width(ring: list[dict], measure: Measure, style: dict, rules: dict) -> float:
    space = rules["label_space"] * style["sizes"]["label"]
    widest = max((measure(segment["name"], "label") + space + measure(segment["share_text"], "label")
                  for segment in ring), default=0.0)
    return (rules["leader_elbow"] + rules["leader_run"] + rules["label_gap"]) * style["base"] + widest


def leader_entries(ring: list[dict], cx: float, cy: float, radius: float, style: dict, rules: dict,
                   spans: list[tuple[float, float]] | None = None) -> list[dict]:
    entries = []
    for segment, (start, end) in zip(ring, spans or ring_spans(ring), strict=True):
        middle = (start + end) / 2
        side = "right" if math.cos(math.radians(middle)) >= -1e-9 else "left"
        entries.append({"segment": segment, "side": side,
                        "anchor": point(cx, cy, radius + rules["leader_offset"] * style["base"], middle),
                        "knee": point(cx, cy, radius + rules["leader_elbow"] * style["base"], middle)})
    return entries


def outside_labels(ring: list[dict], cx: float, cy: float, radius: float, box: Box, measure: Measure,
                   style: dict, rules: dict, spans: list[tuple[float, float]] | None = None) -> list[dict]:
    line, base = line_height(style, "label"), style["base"]
    reach = radius + (rules["leader_elbow"] + rules["leader_run"]) * base
    primitives = []
    entries = leader_entries(ring, cx, cy, radius, style, rules, spans)
    for side, direction in (("left", -1), ("right", 1)):
        group = [entry for entry in entries if entry["side"] == side]
        ys = spread_labels([entry["knee"][1] for entry in group], line, box.y + line / 2,
                           box.y + box.height - line / 2)
        for entry, y in zip(group, ys, strict=True):
            end_x = cx + direction * reach
            primitives.append({"kind": "line", "points": [entry["anchor"], [entry["knee"][0], y], [end_x, y]],
                               "color": style["neutral"]["axis"], "width": style["leader_width"]})
            primitives += label_pair(entry["segment"], end_x + direction * rules["label_gap"] * base, y, side,
                                     measure, style, rules)
    return primitives


def centre_total(total: str | None, label: str | None, cx: float, cy: float, style: dict) -> list[dict]:
    if total is None:
        return []
    neutral, caption_line = style["neutral"], line_height(style, "caption")
    value_baseline = baseline_for(cy, style, "panel") - (caption_line / 2 if label else 0.0)
    primitives = [text(cx, value_baseline, total, "panel", neutral["ink"], "center")]
    if label:
        primitives.append(text(cx, value_baseline + caption_line, label, "caption", neutral["muted"], "center"))
    return primitives


def key_rows(rings: list[list[dict]]) -> list[tuple[int, dict]]:
    """Segments depth first: each parent followed by its children, in drawing order."""
    def children(depth: int, parent: int | None) -> list[tuple[int, dict]]:
        if depth == len(rings):
            return []
        rows = []
        for segment in rings[depth]:
            if segment["parent"] == parent:
                rows += [(depth, segment)] + children(depth + 1, segment["index"])
        return [row for row in rows if not repeats_parent(row, rows)]
    return children(0, None)


def repeats_parent(row: tuple[int, dict], rows: list[tuple[int, dict]]) -> bool:
    """An only child named like its parent (an unsplit category) adds nothing to the key."""
    depth, segment = row
    parents = [item for level, item in rows if level == depth - 1 and item["index"] == segment["parent"]]
    return bool(parents) and parents[0]["name"] == segment["name"] and parents[0]["share"] == segment["share"]


def key_right(rows: list[tuple[int, dict]], x: float, right: float, measure: Measure, style: dict,
              rules: dict) -> float:
    """Shares right-aligned just past the longest name, not at the far edge of a wide panel."""
    base = style["base"]
    names = max(depth * rules["key_indent"] * base + measure(segment["name"], "label") for depth, segment in rows)
    shares = max(measure(segment["share_text"], "label") for _, segment in rows)
    return min(right, x + (style["swatch"] + style["swatch_text"] + rules["key_gap"]) * base + names + shares)


def square(x: float, y: float, side: float, fill: str) -> dict:
    return {"kind": "polygon", "points": [[x, y], [x + side, y], [x + side, y + side], [x, y + side]], "fill": fill}


def hierarchical_key(rings: list[list[dict]], x: float, right: float, cy: float, measure: Measure, style: dict,
                     rules: dict) -> list[dict]:
    base, neutral, rows = style["base"], style["neutral"], key_rows(rings)
    right = key_right(rows, x, right, measure, style, rules)
    pitch, side = line_height(style, "label") + rules["key_row_gap"] * base, style["swatch"] * base
    top, primitives = cy - pitch * len(rows) / 2, []
    for row, (depth, segment) in enumerate(rows):
        centre, left = top + pitch * (row + 0.5), x + depth * rules["key_indent"] * base
        baseline = baseline_for(centre, style, "label")
        primitives += [square(left, centre - side / 2, side, segment["color"]),
                       text(left + side + style["swatch_text"] * base, baseline, segment["name"], "label",
                            neutral["ink"]),
                       text(right, baseline, segment["share_text"], "label", neutral["muted"], "right")]
    return primitives


def inside_sector(point_xy: list[float], centre: tuple[float, float], radii: tuple[float, float],
                  span: tuple[float, float], pad: float) -> bool:
    dx, dy = point_xy[0] - centre[0], centre[1] - point_xy[1]
    radius = math.hypot(dx, dy)
    if not radii[0] + pad <= radius <= radii[1] - pad:
        return False
    angle_pad = math.degrees(pad / radius)
    offset = (span[0] - angle_pad - math.degrees(math.atan2(dy, dx))) % 360
    return offset <= span[0] - span[1] - 2 * angle_pad


def text_fits(x: float, y: float, width: float, height: float, centre: tuple[float, float],
              radii: tuple[float, float], span: tuple[float, float], pad: float) -> bool:
    """Points around the text's box (corners and edges) all inside the padded ring sector."""
    steps = [index / 4 for index in range(5)]
    left, top = x - width / 2, y - height / 2
    outline = [[left + width * step, top + height * edge] for step in steps for edge in (0, 1)] + [
        [left + width * edge, top + height * step] for step in steps for edge in (0, 1)]
    return all(inside_sector(item, centre, radii, span, pad) for item in outline)


def ring_label(segment: dict, span: tuple[float, float], radii: tuple[float, float], cx: float, cy: float,
               measure: Measure, style: dict, rules: dict) -> list[dict]:
    if segment["share"] < rules["ring_min_share"]:
        return []
    x, y = point(cx, cy, (radii[0] + radii[1]) / 2, (span[0] + span[1]) / 2)
    height, pad = style["cap_height"] * style["sizes"]["label"], rules["ring_label_pad"] * style["base"]
    candidates = [f"{segment['name']} {segment['share_text']}", segment["share_text"]]
    fitting = [content for content in candidates
               if text_fits(x, y, measure(content, "label"), height, (cx, cy), radii, span, pad)]
    if not fitting:
        return []
    neutral = style["neutral"]
    color = neutral["ink"] if contrast(segment["color"], neutral["ink"]) >= contrast(
        segment["color"], neutral["surface"]) else neutral["surface"]
    return [text(x, baseline_for(y, style, "label"), fitting[0], "label", color, "center")]


def ring_labels(rings: list[list[dict]], radii: list[tuple[float, float]], cx: float, cy: float,
                measure: Measure, style: dict, rules: dict) -> list[dict]:
    primitives = []
    for ring, ring_radius in zip(rings, radii, strict=True):
        for segment, span in zip(ring, ring_spans(ring), strict=True):
            primitives += ring_label(segment, span, ring_radius, cx, cy, measure, style, rules)
    return primitives


def donut_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    """All shapes and texts of one donut inside `box` (pt from the figure's top-left corner)."""
    rules, rings, base = load_tokens()["donut"], spec["rings"], style["base"]
    hole = rules["hole"] if len(rings) == 1 else rules["hole_nested"]
    if spec["labels"] == "outside":
        side = outside_width(rings[0], measure, style, rules)
        radius = max(min(box.height / 2, (box.width - 2 * side) / 2), rules["min_radius"] * base)
        cx = box.x + box.width / 2
    elif spec["labels"] == "key":
        radius = min(box.height / 2, box.width * rules["key_share"] / 2)
        cx = box.x + radius
    else:
        radius, cx = min(box.height, box.width) / 2, box.x + box.width / 2
    cy = box.y + box.height / 2
    radii = ring_radii(len(rings), radius, hole, rules["gap_pt"])
    primitives = segment_shapes(rings, cx, cy, radii, rules)
    if spec["labels"] == "outside":
        primitives += outside_labels(rings[0], cx, cy, radius, box, measure, style, rules)
    elif spec["labels"] == "key":
        primitives += hierarchical_key(rings, cx + radius + rules["key_gap"] * base, box.x + box.width, cy, measure,
                                       style, rules)
    else:
        primitives += ring_labels(rings, radii, cx, cy, measure, style, rules)
    return primitives + centre_total(spec["total"], spec["total_label"], cx, cy, style)
