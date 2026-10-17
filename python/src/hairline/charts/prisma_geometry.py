"""PRISMA flow geometry in pt: main boxes outlined, exclusion boxes in the band colour to their right, arrows in
the axis colour, phases as rotated labels on brackets at the left. Pure, like the donut geometry."""

from __future__ import annotations

from hairline.charts.donut_geometry import Measure, line_height, text
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens


def wrap(paragraphs: list[str], width: float, measure: Measure) -> list[str]:
    lines = []
    for paragraph in paragraphs:
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}" if current else word
            if current and measure(candidate, "label") > width:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
    return lines


def rectangle(left: float, top: float, width: float, height: float) -> list[list[float]]:
    return [[left, top], [left + width, top], [left + width, top + height], [left, top + height]]


def arrow(start: list[float], end: list[float], style: dict, rules: dict) -> list[dict]:
    """A line in the axis colour ending in a small filled head."""
    size, color = rules["arrow_head"] * style["base"], style["neutral"]["faint"]
    if start[0] == end[0]:
        head = [[end[0], end[1]], [end[0] - size / 2, end[1] - size], [end[0] + size / 2, end[1] - size]]
        stop = [end[0], end[1] - size]
    else:
        head = [[end[0], end[1]], [end[0] - size, end[1] - size / 2], [end[0] - size, end[1] + size / 2]]
        stop = [end[0] - size, end[1]]
    return [{"kind": "line", "points": [start, stop], "color": color, "width": style["leader_width"], "role": "arrow"},
            {"kind": "polygon", "points": head, "fill": color, "role": "arrow_head"}]


def box_texts(lines: list[str], left: float, top: float, style: dict, pad: float) -> list[dict]:
    size, line = style["sizes"]["label"], line_height(style, "label")
    return [{**text(left + pad, top + pad + style["cap_height"] * size + index * line, content, "label",
                    style["neutral"]["ink"]), "part": "box_text"} for index, content in enumerate(lines)]


def phase_shapes(spec: dict, rows: list[tuple[float, float]], left: float, style: dict, rules: dict) -> list[dict]:
    size, base = style["sizes"]["label"], style["base"]
    text_x = left + style["cap_height"] * size
    bracket_x = left + line_height(style, "label") + rules["bracket_gap"] * base
    tick, shapes = rules["bracket_tick"] * base, []
    for name, first, last in spec["phases"]:
        top, bottom = rows[first][0], rows[last][0] + rows[last][1]
        shapes.append({"kind": "line", "points": [[bracket_x + tick, top], [bracket_x, top], [bracket_x, bottom],
                                                  [bracket_x + tick, bottom]],
                       "color": style["neutral"]["axis"], "width": style["leader_width"]})
        shapes.append({**text(text_x, (top + bottom) / 2, name, "label", style["neutral"]["muted"], "center"),
                       "rotation": 90, "part": "phase"})
    return shapes


def prisma_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    rules, base, line = load_tokens()["prisma"], style["base"], line_height(style, "label")
    pad, gap = rules["box_pad"] * base, rules["column_gap"] * base
    phase_width = line + rules["bracket_gap"] * base + rules["bracket_tick"] * base + gap / 2
    main_left = box.x + phase_width
    main_width = (box.width - phase_width - gap) * rules["main_share"]
    side_left, side_width = main_left + main_width + gap, box.x + box.width - (main_left + main_width + gap)
    shapes, places, top = [], [], box.y
    for row in spec["rows"]:
        main = wrap(row["main"], main_width - 2 * pad, measure)
        side = wrap(row["exclusion"], side_width - 2 * pad, measure) if row["exclusion"] else []
        height = max(len(main), len(side)) * line + 2 * pad
        shapes.append({"kind": "polygon", "points": rectangle(main_left, top, main_width, height),
                       "fill": style["neutral"]["surface"], "edge": style["neutral"]["axis"],
                       "edge_width": style["axis_width"], "role": "main"})
        shapes += box_texts(main, main_left, top, style, pad)
        if side:
            shapes.append({"kind": "polygon", "points": rectangle(side_left, top, side_width, height),
                           "fill": style["neutral"]["band"], "role": "exclusion"})
            shapes += box_texts(side, side_left, top, style, pad)
            shapes += arrow([main_left + main_width, top + height / 2], [side_left, top + height / 2], style, rules)
        if places:
            centre = main_left + main_width / 2
            shapes += arrow([centre, places[-1][0] + places[-1][1]], [centre, top], style, rules)
        places.append((top, height))
        top += height + rules["row_gap"] * base
    return shapes + phase_shapes(spec, places, box.x, style, rules)
