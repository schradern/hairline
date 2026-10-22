"""Venn diagram geometry in pt: two or three circles at fixed schematic positions (or, for two sets, areas
proportional to the counts), each region's count inside it and the set names outside. Names wrap when the circles
would fall below the minimum radius; a diagram taller than the panel starts at its top and the figure grows. Pure."""

from __future__ import annotations

import math

from hairline.charts.donut_geometry import Measure, arc, baseline_for, line_height, text
from hairline.charts.tips import tagged
from hairline.charts.wrapping import pair_lines, pair_width
from hairline.errors import HairlineLayoutError
from hairline.layout.geometry import Box
from hairline.marks import point_fill
from hairline.tokens import load_tokens

# Unit layouts (y up, radius 1): centres, the direction of each set's name, and a point inside each region.
CENTRES = {2: [(-0.5, 0.0), (0.5, 0.0)], 3: [(-0.5, 0.33), (0.5, 0.33), (0.0, -0.5)]}
NAME_ANGLES = [150.0, 30.0, 270.0]
REGION_POINTS = {(0,): (-0.95, 0.65), (1,): (0.95, 0.65), (2,): (0.0, -1.05), (0, 1): (0.0, 0.75),
                 (0, 2): (-0.6, -0.35), (1, 2): (0.6, -0.35), (0, 1, 2): (0.0, 0.05)}


def lens_area(first: float, second: float, distance: float) -> float:
    """Area shared by two circles with these radii, `distance` apart."""
    if distance >= first + second:
        return 0.0
    if distance <= abs(first - second):
        return math.pi * min(first, second) ** 2
    one = max(-1.0, min(1.0, (distance ** 2 + first ** 2 - second ** 2) / (2 * distance * first)))
    two = max(-1.0, min(1.0, (distance ** 2 + second ** 2 - first ** 2) / (2 * distance * second)))
    kite = ((-distance + first + second) * (distance + first - second) * (distance - first + second)
            * (distance + first + second))
    return first ** 2 * math.acos(one) + second ** 2 * math.acos(two) - 0.5 * math.sqrt(max(0.0, kite))


def separation(first: float, second: float, area: float, rules: dict) -> float:
    """Distance between the centres at which the circles share `area` (bisection; apart when nothing is shared)."""
    if area <= 0:
        return first + second + rules["apart"]
    low, high = abs(first - second), first + second
    for _ in range(rules["iterations"]):
        middle = (low + high) / 2
        if lens_area(first, second, middle) > area:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def unit_circles(spec: dict, rules: dict) -> list[tuple[float, float, float]]:
    """Centre x, centre y and radius of each set in unit space."""
    if not spec["proportional"]:
        return [(x, y, 1.0) for x, y in CENTRES[len(spec["sets"])]]
    sizes = [entry["value"] for entry in spec["sets"]]
    largest = max(sizes)
    first, second = math.sqrt(sizes[0] / largest), math.sqrt(sizes[1] / largest)
    distance = separation(first, second, math.pi * spec["regions"][2]["value"] / largest, rules)
    return [(-distance / 2, 0.0, first), (distance / 2, 0.0, second)]


def region_point(members: list[int], circles: list[tuple[float, float, float]]) -> tuple[float, float]:
    """Label point of a region: fixed for three sets, between the circle edges on the centre line for two."""
    if len(circles) == 3:
        return REGION_POINTS[tuple(members)]
    (x1, _, r1), (x2, _, r2) = circles
    edges = {(0,): (x1 - r1, x2 - r2), (1,): (x1 + r1, x2 + r2), (0, 1): (x2 - r2, x1 + r1)}[tuple(members)]
    return (sum(edges) / 2, 0.0)


def name_label(entry: dict, lines: list[str], circle: tuple[float, float, float], angle: float, scale: float,
               origin: tuple, measure: Measure, style: dict, rules: dict) -> list[dict]:
    """Name in ink and size in muted, set off the circle in the direction of `angle`; a wrapped name takes
    `lines`, aligned away from the circle, with the size after the last (alone after an empty last line)."""
    cos, sin = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    gap, size, neutral = rules["label_gap"] * style["base"], style["sizes"]["label"], style["neutral"]
    x = origin[0] + (circle[0] + cos * circle[2]) * scale + cos * gap
    y = origin[1] - (circle[1] + sin * circle[2]) * scale - sin * gap
    space, line, count = load_tokens()["donut"]["label_space"] * size, line_height(style, "label"), len(lines)
    value = measure(entry["value_text"], "label")
    widths = [measure(content, "label") for content in lines]
    widths[-1] = widths[-1] + space + value if lines[-1] else value
    cutoff = rules["side_cutoff"]
    if sin > cutoff:
        first = y - style["descender"] * size - (count - 1) * line
    elif sin < -cutoff:
        first = y + style["cap_height"] * size
    else:
        first = baseline_for(y - (count - 1) * line / 2, style, "label")
    shapes = []
    for index, (content, width) in enumerate(zip(lines, widths, strict=True)):
        start = x - width if cos < -cutoff else x if cos > cutoff else x - width / 2
        if content:
            shapes.append(text(start, first + index * line, content, "label", neutral["ink"]))
    return shapes + [text(start + width - value, first + (count - 1) * line, entry["value_text"], "label",
                          neutral["muted"])]


def venn_shapes(spec: dict, circles: list, scale: float, origin: tuple, measure: Measure, style: dict,
                rules: dict, names: list[list[str]] | None = None) -> list[dict]:
    fills, outlines, labels = [], [], []
    for entry, (x, y, radius) in zip(spec["sets"], circles, strict=True):
        points = arc(origin[0] + x * scale, origin[1] - y * scale, radius * scale, 90.0, -270.0, rules["arc_step"])
        fills.append(tagged({"kind": "polygon", "role": "set", "name": entry["name"], "points": points,
                             "fill": entry["color"], "alpha": rules["fill_opacity"]},
                            entry["name"], f"{entry['name']}: {entry['value_text']}"))
        outlines.append({"kind": "line", "points": points, "width": style["data_width"],
                         "color": point_fill(entry["color"], style["neutral"]["surface"])})
    for region in spec["regions"]:
        if spec["proportional"] and region["value"] == 0:
            continue
        x, y = region_point(region["sets"], circles)
        labels.append(text(origin[0] + x * scale, baseline_for(origin[1] - y * scale, style, "label"),
                           region["value_text"], "label", style["neutral"]["ink"], "center"))
    names = names or [[entry["name"]] for entry in spec["sets"]]
    for entry, lines, circle, angle in zip(spec["sets"], names, circles, NAME_ANGLES, strict=False):
        labels += name_label(entry, lines, circle, angle, scale, origin, measure, style, rules)
    return fills + outlines + labels


def shape_bounds(shapes: list[dict], measure: Measure, style: dict) -> tuple[float, float, float, float]:
    """Left, top, right and bottom of the shapes, texts from their width, cap height and descender."""
    xs, ys = [], []
    for shape in shapes:
        if shape["kind"] == "text":
            width, size = measure(shape["text"], shape["role"]), style["sizes"][shape["role"]]
            left = shape["x"] - {"left": 0.0, "center": width / 2, "right": width}[shape["align"]]
            xs += [left, left + width]
            ys += [shape["y"] - style["cap_height"] * size, shape["y"] + style["descender"] * size]
        else:
            xs += [point[0] for point in shape["points"]]
            ys += [point[1] for point in shape["points"]]
    return min(xs), min(ys), max(xs), max(ys)


def wrapped_names(spec: dict, width: float, measure: Measure, style: dict) -> list[list[str]]:
    """Set names wrapped so that each line, the last with its size, is at most `width` wide."""
    space = load_tokens()["donut"]["label_space"] * style["sizes"]["label"]
    return [pair_lines(entry["name"], width, measure, measure(entry["value_text"], "label"), space)
            for entry in spec["sets"]]


def name_lines(spec: dict, fits, measure: Measure, style: dict, rules: dict) -> list[list[str]] | None:
    """One line per name while the diagram is narrow enough with circles of the minimum radius (`fits`);
    otherwise the widest wrap that is, or None when even a word per line is too wide."""
    space = load_tokens()["donut"]["label_space"] * style["sizes"]["label"]
    names = [[entry["name"]] for entry in spec["sets"]]
    if fits(names):
        return names
    narrowest = wrapped_names(spec, 0.0, measure, style)
    if not fits(narrowest):
        return None
    low = max(pair_width(lines, measure, measure(entry["value_text"], "label"), space)
              for entry, lines in zip(spec["sets"], narrowest, strict=True))
    high = max(pair_width(lines, measure, measure(entry["value_text"], "label"), space)
               for entry, lines in zip(spec["sets"], names, strict=True))
    for _ in range(rules["iterations"]):
        middle = (low + high) / 2
        low, high = (middle, high) if fits(wrapped_names(spec, middle, measure, style)) else (low, middle)
    return wrapped_names(spec, low, measure, style)


def venn_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    rules = load_tokens()["venn"]
    circles = unit_circles(spec, rules)

    def bounds(scale: float, names: list[list[str]]) -> tuple[float, float, float, float]:
        return shape_bounds(venn_shapes(spec, circles, scale, (0.0, 0.0), measure, style, rules, names), measure,
                            style)

    def narrow(scale: float, names: list[list[str]]) -> bool:
        left, _, right, _ = bounds(scale, names)
        return right - left <= box.width

    def fits(scale: float, names: list[list[str]]) -> bool:
        left, top, right, bottom = bounds(scale, names)
        return right - left <= box.width and bottom - top <= box.height

    low, high = load_tokens()["donut"]["min_radius"] * style["base"], max(box.width, box.height)
    names = name_lines(spec, lambda lines: narrow(low, lines), measure, style, rules)
    if names is None:
        left, _, right, _ = bounds(low, wrapped_names(spec, 0.0, measure, style))
        raise HairlineLayoutError(f"hairline: venn: the set names need {right - left:.0f} pt across beside circles "
                                  f"of the smallest size, but the figure leaves {box.width:.0f} pt. Shorten the set "
                                  "names or use a wider size")
    if fits(low, names):
        for _ in range(rules["iterations"]):
            middle = (low + high) / 2
            low, high = (middle, high) if fits(middle, names) else (low, middle)
    left, top, right, bottom = bounds(low, names)
    origin = (box.x + (box.width - (right - left)) / 2 - left,
              box.y + max(0.0, box.height - (bottom - top)) / 2 - top)
    return venn_shapes(spec, circles, low, origin, measure, style, rules, names)
