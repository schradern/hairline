"""Risk-of-bias summary geometry in pt: one 100 % bar per domain, counts inside, the overall row below a rule."""

from __future__ import annotations

from hairline.charts.correlation_geometry import text_color
from hairline.charts.donut_geometry import Measure, baseline_for, line_height, text
from hairline.charts.tips import tagged
from hairline.charts.wrapping import fit_lines, widest_line
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


def domain_lines(spec: dict, box: Box, measure: Measure, style: dict, rules: dict) -> tuple[list[list[str]], float]:
    """Each domain's lines and the width of the label column: one line while the bars keep `min_plot`, wrapped
    into the room that leaves otherwise."""
    gap, least = rules["label_gap"] * style["base"], rules["min_plot"] * style["base"]
    labels = max(measure(domain, "label") for domain in spec["domains"]) + gap
    if box.width - labels >= least:
        return [[domain] for domain in spec["domains"]], labels
    weights = [600 if index == spec["overall"] else None for index in range(len(spec["domains"]))]
    lines = [fit_lines(domain, box.width - least - gap, measure, "risk of bias", "the domain", weight=weight)
             for domain, weight in zip(spec["domains"], weights, strict=True)]
    return lines, max(widest_line(name, measure, weight=weight)
                      for name, weight in zip(lines, weights, strict=True)) + gap


def risk_of_bias_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    """Rows from the top; a wrapped domain makes its row as tall as its lines, its bar centred beside them."""
    rules, base = load_tokens()["risk_of_bias"], style["base"]
    rows, overall, line = len(spec["domains"]), spec["overall"], line_height(style, "label")
    names, labels = domain_lines(spec, box, measure, style, rules)
    extra = rules["overall_gap"] * base if overall is not None else 0.0
    height = min(rules["max_bar"] * base, (box.height - extra - (rows - 1) * rules["row_gap"] * base) / rows)
    shapes, top = [], box.y
    for index, (domain, lines, counts) in enumerate(zip(spec["domains"], names, spec["counts"], strict=True)):
        if index == overall:
            divider = top - rules["row_gap"] * base / 2 + extra / 2
            shapes.append({"kind": "line", "points": [[box.x, divider], [box.x + box.width, divider]],
                           "color": style["neutral"]["axis"], "width": style["leader_width"], "part": "rule"})
            top += extra
        row = height if len(lines) == 1 else max(height, len(lines) * line)
        first = top + row / 2 - (len(lines) - 1) * line / 2
        shapes += [text(box.x, baseline_for(first + number * line, style, "label"), content, "label",
                        style["neutral"]["ink"], "left", 600 if index == overall else None)
                   for number, content in enumerate(lines)]
        shapes += segments(counts, box.x + labels, box.x + box.width, top + (row - height) / 2, height,
                           spec["colors"], measure, style, rules["gap_pt"], domain)
        top += row + rules["row_gap"] * base
    return shapes
