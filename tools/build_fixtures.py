"""Write shared expected values (tokens/fixtures/*.json) from the reference Python implementation.

The R package must reproduce every value in these files; regenerate them only when an algorithm
changes on purpose, and review the diff.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import pandas as pd

from hairline.brand import load_brand
from hairline.charts.common import fold_other
from hairline.charts.donut import donut_rings
from hairline.charts.donut_geometry import donut_drawing
from hairline.charts.labels import spread_labels
from hairline.charts.partition import partition_drawing
from hairline.color.adapt import adapt_readable
from hairline.color.check import check_palette
from hairline.color.space import hex_to_oklch
from hairline.color.tints import tints
from hairline.color.vision import contrast, delta_e, simulate
from hairline.entities import assign_colors
from hairline.layout.frame import compute_frame
from hairline.layout.geometry import Box, frame_input_from_dict, load_font_metrics
from hairline.marks import point_fill, point_step
from hairline.numbers import format_number, format_percent
from hairline.settings import use
from hairline.ticks import nice_breaks
from hairline.tokens import load_tokens

REPO = Path(__file__).resolve().parents[1]

FIXTURES = REPO / "tokens" / "fixtures"
SAMPLE_COLORS = ["#2474cf", "#e8a628", "#53b0de", "#b93780", "#44aa5a", "#8362cd", "#ef675a", "#00afa9",
                 "#14325c", "#e8574f", "#8fc1f2", "#9ee0b4", "#ffffff", "#000000", "#6f757d", "#1b1e22"]


def colour_cases() -> dict[str, list[dict]]:
    pairs = list(itertools.combinations(SAMPLE_COLORS[:8], 2))[:12]
    return {
        "oklch": [{"hex": color, "oklch": list(hex_to_oklch(color))} for color in SAMPLE_COLORS],
        "simulate": [{"hex": color, "kind": kind, "result": simulate(color, kind)}
                     for color in SAMPLE_COLORS[:8] for kind in ("protan", "deutan")],
        "delta_e": [{"a": a, "b": b, "kind": kind, "value": delta_e(a, b, kind)}
                    for a, b in pairs for kind in (None, "protan", "deutan")],
        "contrast": [{"a": color, "b": "#ffffff", "value": contrast(color, "#ffffff")} for color in SAMPLE_COLORS],
    }


def check_cases() -> dict[str, list[dict]]:
    tokens = load_tokens()
    inputs = [(colors, pairs) for colors in tokens["palettes"].values() for pairs in ("adjacent", "all")]
    inputs += [(["#14325c", "#e8574f", "#8fc1f2", "#9ee0b4"], "adjacent"), (["#2474cf"], "adjacent"),
               (["#44aa5a", "#e8a628", "#b93780"], "adjacent"), (["#009775", "#e8a628", "#b93780"], "all")]
    checks = []
    for colors, pairs in inputs:
        report = check_palette(colors, pairs=pairs)
        checks.append({"colors": colors, "pairs": pairs, "passed": report.passed, "worst_cvd": report.worst_cvd,
                       "worst_normal": report.worst_normal, "head_all_pairs": report.head_all_pairs,
                       "light_slots": report.light_slots, "failures": len(report.failures),
                       "warnings": len(report.warnings)})
    brands = [["#14325c", "#e8574f", "#8fc1f2", "#9ee0b4"], ["#0b3d6e", "#f2545b", "#8cc8ff", "#7fd8a0"],
              tokens["palettes"]["daylight"]]
    return {"checks": checks, "adapt": [{"colors": colors, "adapted": adapt_readable(colors)} for colors in brands],
            "ramps": tokens["ramps"]}


NUMBER_VALUES = [0, 0.5, -0.5, -0.04, 1.005, 2184, -2184.5, 1234567.891, 0.000123, 99.95]
BREAK_RANGES = [(0, 100), (0.21, 0.88), (3, 3), (0, 1), (-7, 13), (1e-3, 9e-3), (0, 546), (0, 0), (-1, -1),
                (99, 101), (0.15, 1.04), (2, 14), (0, 36), (-1.6, 1.0), (0, 0.6), (0, 8), (0, 20), (0, 25),
                (12, 87), (-0.3, 0.3), (0.2, 5), (1e5, 3e5), (0.6, 0.6), (1, 1000), (-50, -10), (0.001, 0.002)]


def number_cases() -> list[dict]:
    cases = []
    for value in NUMBER_VALUES:
        for digits in (0, 1, 2):
            for locale in ("en", "de"):
                cases.append({"kind": "number", "value": value, "digits": digits, "locale": locale,
                              "result": format_number(value, digits, locale)})
                cases.append({"kind": "percent", "value": value / 100, "digits": digits, "locale": locale,
                              "result": format_percent(value / 100, digits, locale)})
    return cases


def break_cases() -> list[dict]:
    return [{"low": low, "high": high, "breaks": nice_breaks(low, high)} for low, high in BREAK_RANGES]


FRAME_SIZES = {"title": 13.5, "subtitle": 9.0, "panel": 9.0, "label": 8.1, "caption": 7.65}
FRAME_CASES = [
    {"width_pt": 482, "height_pt": 361},
    {"width_pt": 482, "height_pt": 361, "subtitle_lines": 1, "legend_rows": 1, "caption_lines": 1, "y_title": True},
    {"width_pt": 241, "height_pt": 181, "title_lines": 2, "subtitle_lines": 2, "caption_lines": 2},
    {"width_pt": 493, "height_pt": 600, "subtitle_lines": 1, "legend_rows": 1, "caption_lines": 1, "panel_rows": 4,
     "panel_header_lines": [1, 1, 1, 1], "y_label_width_pt": 18},
    {"width_pt": 493, "height_pt": 420, "legend_rows": 2, "panel_rows": 2, "panel_columns": 3,
     "panel_header_lines": [1, 1], "x_title": True, "y_title": True, "y_label_width_pt": 14},
    {"width_pt": 340, "height_pt": 260, "subtitle_lines": 1, "panel_columns": 2, "panel_header_lines": [2]},
    {"width_pt": 720, "height_pt": 405, "subtitle_lines": 1, "caption_lines": 1, "x_tick_labels": False},
    {"width_pt": 482, "height_pt": 361, "subtitle_lines": 1, "panel_header_lines": [2], "y_title": True,
     "x_title": True, "caption_lines": 3, "y_label_width_pt": 25},
    {"width_pt": 493, "height_pt": 420, "panel_rows": 2, "panel_columns": 2, "panel_header_lines": [1, 1],
     "y_label_width_pt": 14, "column_label_widths": [14, 22.5], "x_tick_rows": [True, True]},
    {"width_pt": 493, "height_pt": 420, "subtitle_lines": 1, "panel_rows": 2, "panel_columns": 3,
     "panel_header_lines": [1, 1], "y_label_width_pt": 12, "x_tick_rows": [True, True]},
    {"width_pt": 482, "height_pt": 361, "subtitle_lines": 1, "caption_lines": 1, "y_labels": False,
     "x_tick_labels": False},
]


def frame_cases() -> list[dict]:
    metrics, cases = load_font_metrics(), []
    for values in FRAME_CASES:
        spec = {"base_size": 9.0, "sizes": FRAME_SIZES, **values}
        frame_input = frame_input_from_dict(spec)
        cases.append({"input": spec, "layout": compute_frame(frame_input, metrics).to_dict()})
    return cases


def brand_cases() -> dict:
    brand = load_brand(REPO / "brands" / "example" / "_brand.yml")
    return {"name": brand.name, "names": brand.names, "colors_given": brand.colors_given,
            "readable": brand.colors_used, "neutral": brand.neutral, "sizes": brand.sizes, "locale": brand.locale,
            "base_size": brand.base_size}


def entity_cases() -> list[dict]:
    daylight = load_tokens()["palettes"]["daylight"]
    cases = [
        {"fixed": {}, "requests": ["Unit A", "Unit B", "Unit D"]},
        {"fixed": {"Unit B": daylight[0]}, "requests": ["Unit A", "Unit B", "Unit F"]},
        {"fixed": {"Control": "#5b6168"}, "requests": ["Intervention", "Control"]},
        {"fixed": {"a": daylight[2], "b": daylight[0]}, "requests": ["c", "d", "a"]},
    ]
    built = [{"palette": daylight, "label": "palette 'daylight'", **case,
              "expected": assign_colors(daylight, "palette 'daylight'", case["fixed"], case["requests"])}
             for case in cases]
    built.append({"palette": ["#112233", "#445566"], "label": "custom palette", "fixed": {"a": "#112233"},
                  "requests": ["b", "c"], "error": "custom palette has 2 slots but 3 categories need colours: a, b, c"})
    return built


POINT_COUNTS = [1, 200, 201, 1000, 1001, 5000, 5001, 100000]


def point_cases() -> dict[str, list[dict]]:
    palettes = load_tokens()["palettes"]
    colors = list(dict.fromkeys(SAMPLE_COLORS + [color for slots in palettes.values() for color in slots]))
    return {"fills": [{"hex": color, "surface": "#ffffff", "fill": point_fill(color, "#ffffff")} for color in colors],
            "steps": [{"count": count, "radius": point_step(count)[0], "opacity": point_step(count)[1]}
                      for count in POINT_COUNTS]}


LABEL_CASES = [([0, 10, 20], 5, -100, 100), ([10, 10, 10], 4, -100, 100), ([12, 0, 10], 4, -100, 100),
               ([0, 1, 2], 4, 0, 100), ([0, 0, 0], 10, 0, 10), ([98, 99, 100], 4, 0, 100),
               ([5, 6, 30, 31, 32], 6, 0, 60), ([50], 8, 0, 100), ([], 8, 0, 100), ([3.5, 3.6, 3.7, 90], 7.2, 0, 95),
               ([-20, -19, 40, 41], 9, -30, 50), ([1, 2, 3, 4, 5, 6], 2.5, 0, 12)]
FOLD_CASES = [(list("abcdefghi"), [5, 1, 9, 2, 8, 3, 7, 4, 6], 4), (list("abc"), [1, 2, 3], 7),
              (list("abcdefgh"), [3, 3, 3, 3, 3, 3, 3, 3], 7)]


def chart_helper_cases() -> dict[str, list[dict]]:
    daylight = load_tokens()["palettes"]["daylight"]
    return {"labels": [{"positions": positions, "height": height, "low": low, "high": high,
                        "result": spread_labels(positions, height, low, high)}
                       for positions, height, low, high in LABEL_CASES],
            "tints": [{"color": color, "count": count, "result": tints(color, count)}
                      for color in daylight + ["#14325c", "#b3b8be"] for count in (1, 3, 5)],
            "fold": [{"labels": labels, "values": values, "keep": keep,
                      "result": list(fold_other(labels, values, keep))}
                     for labels, values, keep in FOLD_CASES]}


DRAWING_STYLE = {"base": 9.0, "sizes": {"title": 13.5, "panel": 9.0, "label": 7.2, "caption": 7.2}, "line_gap": 0.25,
                 "cap_height": 0.7, "swatch": 0.85, "swatch_text": 0.5, "leader_width": 0.54,
                 "neutral": {"ink": "#1b1e22", "muted": "#5b6168", "faint": "#6f757d", "axis": "#c4c8cd",
                             "surface": "#ffffff"}}


def fake_measure(text: str, role: str, weight: int | None = None) -> float:
    """Stand-in text width for geometry fixtures, so they do not depend on a font engine."""
    return 0.5 * DRAWING_STYLE["sizes"][role] * len(text)


def donut_cases() -> list[dict]:
    use(brand=False)
    single = pd.DataFrame({"name": ["Home", "Rehabilitation", "Other ward", "Care home", "Died", "Hospice", "Transfer",
                                    "Unknown", "Left"], "n": [412, 168, 97, 54, 23, 9, 7, 3, 2]})
    nested = pd.DataFrame({"route": ["Home", "Home", "Rehabilitation", "Rehabilitation", "Other ward", "Care home"],
                           "detail": ["Alone", "With support", "Inpatient", "Outpatient", "Other ward", "Care home"],
                           "n": [250, 162, 120, 48, 97, 54]})
    inputs = [(single, "name", None, "outside", Box(20, 60, 440, 240)),
              (nested, None, ["route", "detail"], "key", Box(20, 60, 440, 240)),
              (nested, None, ["route", "detail"], "ring", Box(20, 60, 300, 300))]
    cases = []
    for data, label, levels, mode, box in inputs:
        rings = donut_rings(data, label, "n", levels)
        spec = {"rings": rings, "labels": mode, "total": "731", "total_label": "patients"}
        cases.append({"data": data.to_dict(orient="list"), "label": label, "levels": levels, "spec": spec,
                      "box": [box.x, box.y, box.width, box.height],
                      "shapes": donut_drawing(spec, box, fake_measure, DRAWING_STYLE)})
    return cases


def partition_cases() -> list[dict]:
    use(brand=False)
    data = pd.DataFrame({"route": ["Home", "Home", "Rehabilitation", "Rehabilitation", "Other ward", "Care home"],
                         "detail": ["Alone", "With support", "Inpatient", "Outpatient", "Other ward", "Care home"],
                         "n": [250, 162, 120, 48, 97, 54]})
    cases = []
    for levels, box in ((["route", "detail"], Box(20, 60, 440, 200)), (["route"], Box(0, 0, 160, 60))):
        spec = {"rings": donut_rings(data, None, "n", levels), "levels": [level.title() for level in levels]}
        cases.append({"spec": spec, "box": [box.x, box.y, box.width, box.height],
                      "shapes": partition_drawing(spec, box, fake_measure, DRAWING_STYLE)})
    return cases


def write(name: str, content: object) -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    (FIXTURES / name).write_text(json.dumps(content, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    load_tokens()
    write("colour.json", colour_cases())
    write("checks.json", check_cases())
    write("numbers.json", number_cases())
    write("breaks.json", break_cases())
    write("frame.json", frame_cases())
    write("brand.json", brand_cases())
    write("entities.json", entity_cases())
    write("points.json", point_cases())
    write("chart_helpers.json", chart_helper_cases())
    write("donut.json", {"style": DRAWING_STYLE, "cases": donut_cases()})
    write("partition.json", {"style": DRAWING_STYLE, "cases": partition_cases()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
