"""Partition bars: a hierarchy as stacked rows, children directly under their parent."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

from hairline.charts.common import humanise, joined, with_counts
from hairline.charts.donut import donut_rings
from hairline.charts.donut_geometry import Measure, baseline_for, line_height, text
from hairline.charts.tips import tagged
from hairline.color.vision import contrast
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens


def label_lines(segment: dict, room: float, height: float, measure: Measure, style: dict) -> list[str]:
    """Name and share on one line, else name above share, else the share, else nothing."""
    pair = f"{segment['name']} {segment['share_text']}"
    if measure(pair, "label") <= room:
        return [pair]
    if measure(segment["name"], "label") <= room and 2 * line_height(style, "label") <= height:
        return [segment["name"], segment["share_text"]]
    return [segment["share_text"]] if measure(segment["share_text"], "label") <= room else []


def inside_label(segment: dict, left: float, right: float, top: float, height: float, measure: Measure,
                 style: dict, rules: dict) -> list[dict]:
    """Centred in the bar, in ink or surface, whichever contrasts more with the fill."""
    pad = rules["label_pad"] * style["base"]
    lines = label_lines(segment, right - left - 2 * pad, height - pad, measure, style)
    neutral, line = style["neutral"], line_height(style, "label")
    color = neutral["ink"] if contrast(segment["color"], neutral["ink"]) >= contrast(
        segment["color"], neutral["surface"]) else neutral["surface"]
    first = top + height / 2 - line * (len(lines) - 1) / 2
    return [text((left + right) / 2, baseline_for(first + index * line, style, "label"), content, "label", color,
                 "center") for index, content in enumerate(lines)]


def row_shapes(ring: list[dict], box: Box, top: float, height: float, measure: Measure, style: dict,
               rules: dict) -> tuple[list[dict], list[dict]]:
    bars, labels, cumulative, gap = [], [], 0.0, rules["gap_pt"]
    for segment in ring:
        start, end = cumulative, cumulative + segment["share"]
        cumulative = end
        left = box.x + box.width * start + (gap / 2 if start > 1e-9 else 0.0)
        right = box.x + box.width * end - (gap / 2 if end < 1 - 1e-9 else 0.0)
        if right <= left:
            continue
        corners = [[left, top], [right, top], [right, top + height], [left, top + height]]
        bars.append(tagged({"kind": "polygon", "points": corners, "fill": segment["color"]}, segment["name"],
                           f"{segment['name']}: {segment['share_text']}"))
        labels += inside_label(segment, left, right, top, height, measure, style, rules)
    return bars, labels


def partition_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    """One row per level with its name above; bars fill the box width, rows share the height."""
    rules, rings, base = load_tokens()["partition"], spec["rings"], style["base"]
    heading, gap, row_gap = line_height(style, "panel"), rules["heading_gap"] * base, rules["row_gap"] * base
    available = box.height - len(rings) * (heading + gap) - (len(rings) - 1) * row_gap
    height = min(available / len(rings), rules["max_bar"] * base)
    bars, texts, y = [], [], box.y
    for ring, name in zip(rings, spec["levels"], strict=True):
        texts.append(text(box.x, y + style["cap_height"] * style["sizes"]["panel"], name, "panel",
                          style["neutral"]["ink"]))
        top = y + heading + gap
        row_bars, row_labels = row_shapes(ring, box, top, height, measure, style, rules)
        bars, texts, y = bars + row_bars, texts + row_labels, top + height + row_gap
    return bars + texts


def partition(data: pd.DataFrame, levels: Sequence[str], value: str | None = None, *, title: str | None = None,
              subtitle: str | None = None,
              caption: str | None = None, level_names: Sequence[str] | None = None,
              colors: Mapping[str, str] | None = None, size: str = "onehalf") -> HairlineFigure:
    """Partition bars: the documented alternative to a nested donut, read top to bottom."""
    levels = list(levels)
    data, value = with_counts(data, value)
    title = title or f"{humanise(value)} by {joined(levels)}"
    names = list(level_names) if level_names is not None else [humanise(level) for level in levels]
    if len(names) != len(levels):
        raise ValueError(f"hairline: partition: {len(levels)} levels but {len(names)} level name(s); give one name "
                         "per level")
    spec = {"rings": donut_rings(data, None, value, levels, chart="partition", colors=colors), "levels": names}
    result = figure(title, subtitle=subtitle, caption=caption, size=size)
    result.draw(0, lambda box, measure, style: partition_drawing(spec, box, measure, style))
    result.legend([("square", segment["color"], segment["name"]) for segment in spec["rings"][0]])
    return fit_height(result)
