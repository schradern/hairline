"""Risk-of-bias summary geometry in pt: one 100 % bar per domain, counts inside, the overall row below a rule."""

from __future__ import annotations

from hairline.charts.correlation_geometry import text_color
from hairline.charts.donut_geometry import Measure, baseline_for, text
from hairline.charts.tips import tagged
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens

JUDGEMENTS = ("low", "some", "high")


def segments(counts: list[int], left: float, right: float, top: float, height: float, colors: dict,
             measure: Measure, style: dict, gap: float, domain: str = "") -> list[dict]:
    """Low, some concerns and high from left to right, 2 pt apart, each count inside when it fits."""
    total, shapes, start = sum(counts), [], left
    for count, judgement in zip(counts, JUDGEMENTS, strict=True):
        if not count:
            continue
        end = start + (right - left) * count / total
        inner_left, inner_right = start + (gap / 2 if start > left else 0), end - (gap / 2 if end < right - 1e-9 else 0)
        fill = colors[judgement]
        label = load_tokens()["risk_of_bias"]["labels"][judgement]
        shapes.append(tagged({"kind": "polygon", "role": judgement, "fill": fill,
                              "points": [[inner_left, top], [inner_right, top], [inner_right, top + height],
                                         [inner_left, top + height]]},
                             label, f"{domain}, {label}: {count}"))
        if measure(str(count), "label") <= inner_right - inner_left - gap:
            shapes.append(text((inner_left + inner_right) / 2, baseline_for(top + height / 2, style, "label"),
                               str(count), "label", text_color(fill, style), "center"))
        start = end
    return shapes


def risk_of_bias_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    rules, base = load_tokens()["risk_of_bias"], style["base"]
    rows, overall = len(spec["domains"]), spec["overall"]
    labels = max(measure(domain, "label") for domain in spec["domains"]) + rules["label_gap"] * base
    extra = rules["overall_gap"] * base if overall is not None else 0.0
    height = min(rules["max_bar"] * base, (box.height - extra - (rows - 1) * rules["row_gap"] * base) / rows)
    shapes, top = [], box.y
    for index, (domain, counts) in enumerate(zip(spec["domains"], spec["counts"], strict=True)):
        if index == overall:
            divider = top - rules["row_gap"] * base / 2 + extra / 2
            shapes.append({"kind": "line", "points": [[box.x, divider], [box.x + box.width, divider]],
                           "color": style["neutral"]["axis"], "width": style["leader_width"], "part": "rule"})
            top += extra
        shapes.append(text(box.x, baseline_for(top + height / 2, style, "label"), domain, "label",
                           style["neutral"]["ink"], "left", 600 if index == overall else None))
        shapes += segments(counts, box.x + labels, box.x + box.width, top, height, spec["colors"], measure, style,
                           rules["gap_pt"], domain)
        top += height + rules["row_gap"] * base
    return shapes
