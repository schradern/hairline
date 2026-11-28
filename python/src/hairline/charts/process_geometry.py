"""Process diagram geometry in pt: lane names at the left, lanes between hairline rules, one column per stage with
gaps wide enough for the flow labels that start in them, steps as outlined boxes centred in their lane (an accent
outline when highlighted, a dashed one when tentative), note numbers on the boxes' corners and the notes below each
section. Pure; mirrored in R's process_geometry.R."""

from __future__ import annotations

import math

from hairline.charts.donut_geometry import Measure, line_height, text
from hairline.charts.process_routes import flow_label, flow_shapes
from hairline.charts.wrapping import fit_lines, widest_line
from hairline.errors import HairlineLayoutError
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens


def block(count: int, style: dict) -> float:
    """Height of `count` label lines from the first line's cap height to the last baseline."""
    return style["cap_height"] * style["sizes"]["label"] + (count - 1) * line_height(style, "label")


def label_offset(step: dict, rules: dict, base: float) -> float:
    """Room a flow label leaves for the note number on its step's corner."""
    return rules["marker"] * base if step.get("note") else 0.0


def gap_widths(spec: dict, measure: Measure, rules: dict, base: float) -> list[float]:
    """Each gap between stages wide enough for the labels of the flows that leave into it, and room to turn."""
    gaps = [rules["stage_gap"] * base] * (spec["stages"] - 1)
    for section in spec["sections"]:
        for flow in section["flows"]:
            source, target = section["steps"][flow["source"]], section["steps"][flow["target"]]
            if flow["label"] and target["stage"] > source["stage"]:
                need = 2 * rules["label_pad"] * base + label_offset(source, rules, base) + \
                    measure(flow["label"], "label") + rules["turn"] * base
                gaps[source["stage"]] = max(gaps[source["stage"]], need)
    return gaps


def stage_layout(spec: dict, box: Box, measure: Measure, rules: dict, base: float) -> dict:
    """The lane names' column and wrapped names, each stage's left edge, the stages' width and each gap's turn."""
    room = min(max(measure(name, "label") for name in spec["lanes"]), rules["lane_share"] * box.width)
    names = [fit_lines(name, room, measure, "process", "lane name") for name in spec["lanes"]]
    lane_width = max(widest_line(lines, measure) for lines in names)
    gaps = gap_widths(spec, measure, rules, base)
    start = box.x + lane_width + rules["lane_gap"] * base
    width = (box.x + box.width - start - sum(gaps)) / spec["stages"]
    if width < rules["min_stage"] * base:
        need = rules["min_stage"] * base * spec["stages"] + start - box.x + sum(gaps)
        raise HairlineLayoutError(f"hairline: process: {spec['stages']} stages need {need:.0f} pt, but the figure "
                                  f"leaves {box.width:.0f} pt; shorten the flow labels or use a wider size")
    lefts = [start + stage * width + sum(gaps[:stage]) for stage in range(spec["stages"])]
    return {"names": names, "lefts": lefts, "width": width,
            "turns": [lefts[gap + 1] - rules["turn"] * base for gap in range(len(gaps))]}


def section_places(section: dict, layout: dict, top: float, measure: Measure, style: dict,
                   rules: dict) -> tuple[list[dict], list[tuple[float, float]]]:
    """Each step's box and wrapped name, and each lane's top and height: as tall as its tallest box (or name)."""
    base, pad = style["base"], rules["box_pad"] * style["base"]
    lines = [fit_lines(step["name"], layout["width"] - 2 * pad, measure, "process", "step") for step in
             section["steps"]]
    heights = [block(len(names), style) + 2 * pad for names in lines]
    spans, places = [], [None] * len(section["steps"])
    for lane, names in enumerate(layout["names"]):
        boxes = [heights[index] for index, step in enumerate(section["steps"]) if step["lane"] == lane]
        tall = max([block(len(names), style) + 2 * pad, block(1, style) + 2 * pad, *boxes])
        height = tall + 2 * rules["lane_pad"] * base
        centre = top + height / 2
        for index, step in enumerate(section["steps"]):
            if step["lane"] == lane:
                left = layout["lefts"][step["stage"]]
                places[index] = {**step, "lines": lines[index], "left": left, "right": left + layout["width"],
                                 "top": centre - tall / 2, "bottom": centre + tall / 2,
                                 "cx": left + layout["width"] / 2, "cy": centre}
        spans.append((top, height))
        top += height
    return places, spans


def centred_lines(lines: list[str], x: float, centre: float, style: dict, color: str, align: str) -> list[dict]:
    first = centre - block(len(lines), style) / 2 + style["cap_height"] * style["sizes"]["label"]
    return [text(x, first + index * line_height(style, "label"), content, "label", color, align)
            for index, content in enumerate(lines)]


def lane_shapes(spans: list[tuple[float, float]], names: list[list[str]], box: Box, style: dict) -> list[dict]:
    """A hairline above each lane and below the last, the lane's name at the left, centred on the lane."""
    edges = [top for top, _ in spans] + [spans[-1][0] + spans[-1][1]]
    shapes = [{"kind": "line", "points": [[box.x, y], [box.x + box.width, y]], "color": style["neutral"]["axis"],
               "width": style["grid"], "role": "lane_rule"} for y in edges]
    for (top, height), lines in zip(spans, names, strict=True):
        shapes += [{**shape, "part": "lane"} for shape in
                   centred_lines(lines, box.x, top + height / 2, style, style["neutral"]["muted"], "left")]
    return shapes


def marker(x: float, y: float, number: int, color: str, style: dict, rules: dict) -> list[dict]:
    """A note number in a filled circle, its digits in the surface colour."""
    radius, steps = rules["marker"] * style["base"], rules["marker_steps"]
    circle = [[x + radius * math.cos(2 * math.pi * step / steps), y + radius * math.sin(2 * math.pi * step / steps)]
              for step in range(steps)]
    size = style["sizes"]["label"]
    return [{"kind": "polygon", "points": circle, "fill": color, "role": "marker"},
            {**text(x, y + style["cap_height"] * size / 2, str(number), "label", style["neutral"]["surface"],
                    "center", load_tokens()["type"]["key_weight"]), "part": "marker"}]


def step_box(place: dict, style: dict, rules: dict, accent: str) -> list[dict]:
    """The box, outlined in the axis colour, in the accent when highlighted, dashed when tentative; its tooltip."""
    left, top, right, bottom = place["left"], place["top"], place["right"], place["bottom"]
    corners = [[left, top], [right, top], [right, bottom], [left, bottom]]
    shape = {"kind": "polygon", "points": corners, "fill": style["neutral"]["surface"], "role": "step"}
    if place["status"] == "highlight":
        shape |= {"edge": accent, "edge_width": rules["highlight_width"] * style["base"]}
    elif place["status"] is None:
        shape |= {"edge": style["neutral"]["axis"], "edge_width": style["axis_width"]}
    tip = "\n".join(part for part in (place["name"], place["lane_name"], place["note_text"]) if part)
    shapes = [{**shape, "series": place["name"], "tip": tip, "tip_at": [(left + right) / 2, top], "hover_only": True}]
    if place["status"] == "tentative":
        shapes.append({"kind": "line", "points": [*corners, corners[0]], "color": style["neutral"]["faint"],
                       "width": style["axis_width"], "dash": list(rules["dash"]), "role": "step_edge"})
    return shapes


def step_shapes(places: list[dict], style: dict, rules: dict, accent: str) -> list[dict]:
    shapes = []
    for place in places:
        color = style["neutral"]["muted"] if place["status"] == "tentative" else style["neutral"]["ink"]
        shapes += step_box(place, style, rules, accent)
        shapes += [{**shape, "part": "step"} for shape in
                   centred_lines(place["lines"], place["cx"], place["cy"], style, color, "center")]
        if place.get("note"):
            shapes += marker(place["right"], place["top"], place["note"],
                             accent if place["status"] == "highlight" else style["neutral"]["ink"], style, rules)
    return shapes


def note_shapes(notes: list[dict], top: float, box: Box, measure: Measure, style: dict, rules: dict,
                accent: str) -> tuple[list[dict], float]:
    """The notes one under another, each after its number; the bottom of the last."""
    base, line, cap = style["base"], line_height(style, "label"), style["cap_height"] * style["sizes"]["label"]
    indent, shapes = rules["note_indent"] * base, []
    for note in notes:
        lines = fit_lines(note["text"], box.width - indent, measure, "process", "note")
        shapes += marker(box.x + rules["marker"] * base, top + cap / 2, note["number"],
                         accent if note["status"] == "highlight" else style["neutral"]["ink"], style, rules)
        shapes += [{**text(box.x + indent, top + cap + index * line, content, "label", style["neutral"]["muted"]),
                    "part": "note"} for index, content in enumerate(lines)]
        top += cap + (len(lines) - 1) * line + rules["note_gap"] * base + line - cap
    return shapes, top


def process_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    rules, base = load_tokens()["process"], style["base"]
    layout = stage_layout(spec, box, measure, rules, base)
    shapes, top = [], box.y
    for index, section in enumerate(spec["sections"]):
        top += rules["section_gap"] * base if index else 0.0
        if section["name"] is not None:
            baseline = top + style["cap_height"] * style["sizes"]["panel"]
            shapes.append({**text(box.x, baseline, section["name"], "panel", style["neutral"]["ink"]),
                           "part": "section"})
            top = baseline + rules["heading_gap"] * base
        steps = [{**step, "lane_name": spec["lanes"][step["lane"]]} for step in section["steps"]]
        places, spans = section_places({**section, "steps": steps}, layout, top, measure, style, rules)
        cells = {(place["lane"], place["stage"]) for place in places}
        where = f" in section {section['name']!r}" if section["name"] is not None else ""
        shapes += lane_shapes(spans, layout["names"], box, style)
        for flow in section["flows"]:
            shapes += flow_shapes(flow, places, cells, layout["turns"], style, rules, spec["accent"], where)
        shapes += step_shapes(places, style, rules, spec["accent"])
        for flow in section["flows"]:
            source = places[flow["source"]]
            shapes += flow_label(flow, source, places[flow["target"]], measure, style, rules,
                                 label_offset(source, rules, base))
        top = spans[-1][0] + spans[-1][1]
        if section["notes"]:
            notes, top = note_shapes(section["notes"], top + rules["notes_gap"] * base, box, measure, style, rules,
                                     spec["accent"])
            shapes += notes
    return shapes
