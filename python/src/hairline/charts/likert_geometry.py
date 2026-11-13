"""Diverging bars in pt: item names on the left (under their section's heading), each row's bins stacked away from
the split, the split as a line, grid and axis in percent either side, the key numbers beside the plot as in spread.
Pure: the same spec gives the same shapes in both languages."""

from __future__ import annotations

from hairline.charts.donut_geometry import Measure, baseline_for, line_height, text
from hairline.charts.forest_geometry import axis_shapes, fitted_axis, x_scale
from hairline.charts.spread_geometry import axis_title_shape, heading_shapes, pair_texts, section_lines, spread_layout
from hairline.layout.geometry import Box
from hairline.numbers import format_percent
from hairline.tokens import load_tokens


def segments(row: dict, bins: list[dict]) -> list[tuple[dict, float, float, float]]:
    """Each bin's span in percent: a middle level centred on the split, the bins of each side stacked outward from
    it, the one nearest the split first."""
    shares = dict(zip((entry["name"] for entry in bins), row["shares"], strict=True))
    middle = sum(shares[entry["name"]] for entry in bins if entry["side"] == "middle")
    spans = [(entry, -middle / 2, middle / 2, shares[entry["name"]]) for entry in bins if entry["side"] == "middle"]
    edge = -middle / 2
    for entry in reversed([entry for entry in bins if entry["side"] == "left"]):
        spans.append((entry, edge - shares[entry["name"]], edge, shares[entry["name"]]))
        edge -= shares[entry["name"]]
    edge = middle / 2
    for entry in [entry for entry in bins if entry["side"] == "right"]:
        spans.append((entry, edge, edge + shares[entry["name"]], shares[entry["name"]]))
        edge += shares[entry["name"]]
    return spans


def row_bars(row: dict, bins: list[dict], centre: float, line: float, scale, style: dict) -> list[dict]:
    """One rectangle per bin that holds answers, a surface gap between neighbours, each a tooltip target."""
    rules = load_tokens()["likert"]
    half = rules["bar"] * line / 2
    shapes = []
    for entry, low, high, share in segments(row, bins):
        if share <= 0:
            continue
        left, right = scale(low), scale(high)
        shapes.append({"kind": "polygon", "points": [[left, centre - half], [right, centre - half],
                                                     [right, centre + half], [left, centre + half]],
                       "fill": entry["color"], "edge": style["neutral"]["surface"], "edge_width": rules["gap_pt"],
                       "role": "bar", "series": entry["name"],
                       "tip": f"{row['name']}: {entry['name']}, {format_percent(share / 100, 0)}",
                       "tip_at": [(left + right) / 2, centre - half]})
    return shapes


def likert_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    """Rows keep spread's pitch (the figure's height follows them); a heading takes one line."""
    rules = load_tokens()["spread"]
    layout = spread_layout(spec, box, measure, style, rules)
    (left, right), lead = layout["plot"], line_height(style, "label")
    # The axis thinned to the plot's width, before anything is placed on its scale.
    spec = {**spec, "axis": fitted_axis(spec["axis"], False, (left, right), measure, style)}
    scale = x_scale(spec["axis"], False, left, right)
    line = rules["row_pitch"] * lead
    pitch = line + (lead if layout["under"] else 0.0)
    lines = section_lines(spec["rows"])
    heights = [line if kind == "heading" else pitch for kind, _ in lines]
    bottom = box.y + sum(heights)
    shapes = [{"kind": "line", "points": [[scale(value), box.y], [scale(value), bottom]],
               "color": style["neutral"]["grid"], "width": style["grid"], "role": "grid"}
              for value in spec["axis"]["breaks"]]
    top, headings = box.y, 0
    for (kind, entry), height in zip(lines, heights, strict=True):
        centre = top + line / 2
        baseline = baseline_for(centre, style, "label")
        top += height
        if kind == "heading":
            shapes += heading_shapes(str(entry), headings, False, box.x, baseline, measure, style)
            headings += 1
            continue
        shapes += row_bars(entry, spec["bins"], centre, line, scale, style)
        shapes += [text(box.x, baseline, entry["name"], "label", style["neutral"]["ink"])]
        shapes += pair_texts(entry["pairs"], layout["lefts"], baseline + (lead if layout["under"] else 0.0), measure,
                             style)
    split = {"kind": "line", "points": [[scale(0.0), box.y], [scale(0.0), bottom]], "color": style["neutral"]["ink"],
             "width": load_tokens()["likert"]["centre_width"] * style["base"], "role": "split"}
    axis = {"axis": spec["axis"], "favours": None, "null": None}
    return shapes + [split] + axis_shapes(axis, scale, (left, right), bottom, style, rules) + \
        axis_title_shape(spec, right, bottom, style, rules)
