"""Spread rows in pt: group names on the left, range line, interquartile band, median dot and reference tick on a
shared axis with grid lines, the key numbers right-aligned beside the plot (or, on a figure too narrow for both, on
a line under each row), the axis title under the numbers. Pure."""

from __future__ import annotations

from hairline.charts.donut_geometry import Measure, baseline_for, line_height, text
from hairline.charts.forest_geometry import axis_shapes, dot_size, marker, x_scale
from hairline.errors import HairlineLayoutError
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens


def pair_width(pair: list[str], measure: Measure) -> float:
    return measure(f"{pair[0]} ", "label") + measure(pair[1], "label", load_tokens()["type"]["value_weight"])


def stat_widths(spec: dict, measure: Measure) -> list[float]:
    """Width of each key-number column: one column per statistic, so labels line up from row to row."""
    count = max(len(row["pairs"]) for row in spec["rows"])
    return [max((pair_width(row["pairs"][index], measure) for row in spec["rows"] if index < len(row["pairs"])),
                default=0.0) for index in range(count)]


def stat_columns(widths: list[float], start: float, gap: float) -> list[float]:
    """Left edges of the key-number columns from `start`, separated like a panel header's key numbers."""
    lefts, x = [], start
    for width in widths:
        lefts.append(x)
        x += width + gap
    return lefts


def check_room(width: float, block: float, least: float, names: float, gap: float) -> None:
    """Under the rows, a line of key numbers and a row of name and plot must each fit the width."""
    need = max(block, names + gap + least)
    if width < need:
        raise HairlineLayoutError(f"hairline: spread: the figure leaves {width:.0f} pt for the rows, which need at "
                                  f"least {need:.0f} pt: the key numbers take {block:.0f} pt in one line, the group "
                                  f"names {names:.0f} pt beside a plot of {least:.0f} pt. Shorten the group names, "
                                  f"show fewer stats, or use a wider size")


def spread_layout(spec: dict, box: Box, measure: Measure, style: dict, rules: dict) -> dict:
    """The plot span and the key-number columns. The numbers sit right-aligned beside the plot while it keeps at
    least `min_plot`; on a narrower figure they move to a line under each row, from the row's left edge, and the
    plot spans the width the names leave. No statistic is dropped."""
    base, pair_gap = style["base"], load_tokens()["spacing"]["stats_pair"] * style["base"]
    gap, least = rules["column_gap"] * base, rules["min_plot"] * base
    widths = stat_widths(spec, measure)
    block = sum(widths) + pair_gap * (len(widths) - 1) if widths else 0.0
    names = max(measure(row["name"], "label") for row in spec["rows"])
    left, right = box.x + names + gap, box.x + box.width
    if not widths:
        return {"plot": (left, right), "lefts": [], "under": False}
    if right - block - gap - left >= least:
        return {"plot": (left, right - block - gap), "lefts": stat_columns(widths, right - block, pair_gap),
                "under": False}
    check_room(box.width, block, least, names, gap)
    return {"plot": (left, right), "lefts": stat_columns(widths, box.x, pair_gap), "under": True}


def pair_texts(pairs: list[list[str]], lefts: list[float], baseline: float, measure: Measure,
               style: dict) -> list[dict]:
    """Label in faint, value in muted at the value weight: the panel header's key-number style."""
    neutral, weight, shapes = style["neutral"], load_tokens()["type"]["value_weight"], []
    for (label, value), left in zip(pairs, lefts, strict=False):
        shapes += [text(left, baseline, f"{label} ", "label", neutral["faint"]),
                   text(left + measure(f"{label} ", "label"), baseline, value, "label", neutral["muted"], "left",
                        weight)]
    return shapes


def row_shapes(row: dict, centre: float, pitch: float, scale, style: dict, rules: dict) -> list[dict]:
    half = rules["band"] * pitch / 2
    band = [[scale(row["q1"]), centre - half], [scale(row["q3"]), centre - half], [scale(row["q3"]), centre + half],
            [scale(row["q1"]), centre + half]]
    tip = f"{row['name']}: " + ", ".join(f"{label} {value}" for label, value in row["pairs"])
    shapes = [{"kind": "line", "points": [[scale(row["low"]), centre], [scale(row["high"]), centre]],
               "color": style["neutral"]["faint"], "width": style["leader_width"], "role": "range"},
              {"kind": "polygon", "points": band, "fill": row["color"], "alpha": rules["band_opacity"],
               "role": "band", "tip": tip, "tip_at": [scale(row["median"]), centre - half]},
              marker(scale(row["median"]), centre, dot_size(style), "dot", row["color"])]
    if row["mark"] is not None:
        tick, x = rules["mark"] * half, scale(row["mark"])
        shapes.append({"kind": "line", "points": [[x, centre - tick], [x, centre + tick]],
                       "color": style["neutral"]["ink"], "width": style["leader_width"], "role": "mark"})
    return [{**shape, "series": row["name"]} for shape in shapes]


def axis_title_shape(spec: dict, right: float, axis_y: float, style: dict, rules: dict) -> list[dict]:
    if not spec["axis_title"]:
        return []
    size, base = style["sizes"]["label"], style["base"]
    ticks = axis_y + rules["axis_gap"] * base + style["cap_height"] * size
    gap = load_tokens()["spacing"]["x_title"] * base
    baseline = ticks + style["descender"] * size + gap + style["cap_height"] * size
    return [{**text(right, baseline, spec["axis_title"], "label", style["neutral"]["muted"], "right"), "part": "title"}]


def spread_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    """Rows keep their pitch (the figure's height follows them); a row whose numbers sit under it is a line taller."""
    rules = load_tokens()["spread"]
    layout = spread_layout(spec, box, measure, style, rules)
    (left, right), lead = layout["plot"], line_height(style, "label")
    scale = x_scale(spec["axis"], False, left, right)
    line = rules["row_pitch"] * lead
    pitch = line + (lead if layout["under"] else 0.0)
    bottom = box.y + pitch * len(spec["rows"])
    shapes = [{"kind": "line", "points": [[scale(value), box.y], [scale(value), bottom]],
               "color": style["neutral"]["grid"], "width": style["grid"], "role": "grid"}
              for value in spec["axis"]["breaks"]]
    for index, row in enumerate(spec["rows"]):
        centre = box.y + pitch * index + line / 2
        baseline = baseline_for(centre, style, "label")
        shapes += row_shapes(row, centre, line, scale, style, rules)
        shapes += [text(box.x, baseline, row["name"], "label", style["neutral"]["ink"])]
        shapes += pair_texts(row["pairs"], layout["lefts"], baseline + (lead if layout["under"] else 0.0), measure,
                             style)
    axis = {"axis": spec["axis"], "favours": None, "null": None}
    return shapes + axis_shapes(axis, scale, (left, right), bottom, style, rules) + \
        axis_title_shape(spec, right, bottom, style, rules)
