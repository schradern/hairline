"""Write shared expected values (tokens/fixtures/*.json) from the reference Python implementation.

The R package must reproduce every value in these files; regenerate them only when an algorithm
changes on purpose, and review the diff.
"""

from __future__ import annotations

import itertools
import json
import math
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from study_fixtures import spread_cases, study_cases

from hairline.brand import brand_report, load_brand
from hairline.brand_entities import checked_entities
from hairline.charts.arcs import arcs_spec
from hairline.charts.arcs_geometry import arcs_drawing
from hairline.charts.chord import chord_spec
from hairline.charts.chord_geometry import chord_drawing
from hairline.charts.common import fold_other
from hairline.charts.correlation import correlation_spec
from hairline.charts.correlation_geometry import correlation_drawing
from hairline.charts.donut import donut_rings
from hairline.charts.donut_geometry import donut_drawing
from hairline.charts.forest import forest_spec
from hairline.charts.forest_geometry import forest_drawing, log_breaks
from hairline.charts.funnel import funnel_spec
from hairline.charts.funnel_geometry import funnel_drawing
from hairline.charts.heatmap import heatmap_spec
from hairline.charts.heatmap_geometry import heatmap_layout, heatmap_scene
from hairline.charts.labels import spread_labels
from hairline.charts.partition import partition_drawing
from hairline.charts.prisma import prisma_spec
from hairline.charts.prisma_geometry import prisma_drawing
from hairline.charts.raincloud import bracket_levels
from hairline.charts.risk_of_bias import risk_of_bias_spec
from hairline.charts.risk_of_bias_geometry import risk_of_bias_drawing
from hairline.charts.sankey import sankey_spec
from hairline.charts.sankey_geometry import sankey_drawing
from hairline.charts.scatter_density import count_steps, hex_corners, hex_counts, hex_grid
from hairline.charts.surface import surface_spec
from hairline.charts.surface_geometry import pair_layout, scene_shapes, surface_scene
from hairline.charts.swatches_geometry import swatches_drawing
from hairline.charts.venn import venn_spec
from hairline.charts.venn_geometry import venn_drawing
from hairline.charts.waffle import cell_counts, waffle_drawing
from hairline.charts.wrapping import spread_blocks
from hairline.color.adapt import adapt_readable
from hairline.color.check import check_palette
from hairline.color.ramps import diverging_ramp, sequential_ramp
from hairline.color.space import hex_to_oklch
from hairline.color.tints import tints
from hairline.color.vision import contrast, delta_e, simulate
from hairline.entities import assign_colors, chart_colors
from hairline.errors import HairlineLayoutError
from hairline.fonts import nearest_weight
from hairline.layout.frame import compute_frame
from hairline.layout.geometry import Box, frame_input_from_dict, load_font_metrics
from hairline.marks import point_fill, point_step
from hairline.numbers import format_number, format_p, format_percent
from hairline.palettes import swatch_rows
from hairline.settings import use
from hairline.stats.density import bandwidth, density, jitter_offsets, quantiles
from hairline.stats.survival import km_estimate, km_median
from hairline.stats.tests import egger, fit_band, linear_fit, logrank, pearson, rank_sum, spearman
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


NUMBER_VALUES = [0, 0.5, -0.5, -0.04, 1.005, 2184, -2184.5, 1234567.891, 0.000123, 99.95, 8.65, 8.649999999999999,
                 2.45, -2.45, 0.125, 0.25, 2.5, 1234.5, 8.6449]
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
    {"width_pt": 493, "height_pt": 420, "subtitle_lines": 1, "panel_rows": 2, "panel_columns": 3,
     "panel_header_lines": [1, 1], "x_tick_rows": [True, True], "x_title_rows": [True, True], "caption_lines": 1},
    {"width_pt": 493, "height_pt": 300, "panel_columns": 3, "panel_header_lines": [1], "x_title_rows": [True]},
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
    {"width_pt": 482, "height_pt": 361, "subtitle_lines": 1, "caption_lines": 1, "x_title": True, "table_lines": 3,
     "y_label_width_pt": 30},
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
            "base_size": brand.base_size, "layered": layered_brand_case()}


def layered_brand_case() -> dict:
    paths = [REPO / "brands" / "example" / "_brand.yml", REPO / "brands" / "example" / "units.yml"]
    brand, docx = load_brand(paths), load_brand(paths, output="docx")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        exact = checked_entities({"Unit A": "#0b3d6e", "Unit B": "#1d4f86"}, "exact", "test")
    report = [re.sub(r"^(layer \d+): .*$", r"\1", line) for line in brand_report(brand).splitlines()]
    return {"name": brand.name, "entity_colors": brand.entity_colors, "entity_failures": brand.entity_failures,
            "docx_base_size": docx.base_size, "html_grid": load_brand(paths, output="html").neutral["grid"],
            "exact_failures": exact[1], "report": report}


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
    dark = load_tokens()["neutral_dark"]["surface"]
    fills = [{"hex": color, "surface": surface, "fill": point_fill(color, surface)}
             for surface in ("#ffffff", dark) for color in colors + ["#2d1b69", "#0b3d6e"]]
    return {"fills": fills,
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
                 "cap_height": 0.7, "descender": 0.21, "ascender": 0.95, "swatch": 0.85, "swatch_text": 0.5,
                 "leader_width": 0.54,
                 "data_width": 1.26, "axis_width": 0.585,
                 "grid": 0.45, "neutral": {"ink": "#1b1e22", "muted": "#5b6168", "faint": "#6f757d",
                                           "axis": "#c4c8cd", "surface": "#ffffff", "band": "#f2f3f5",
                                           "grid": "#eef0f2"}}


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


WAFFLE_SHARES = [[1 / 3, 1 / 3, 1 / 3], [0.555, 0.445], [0.004, 0.996], [0.7, 0.2, 0.1], [0.125] * 8,
                 [0.333, 0.333, 0.334], [0.0049, 0.0051, 0.99]]


def waffle_cases() -> dict:
    """Cells per slice for shares with ties, slices under half a cell and exact tenths, and the drawing of one
    ring."""
    use(brand=False)
    data = pd.DataFrame({"route": ["Home", "Rehabilitation", "Other ward", "Care home", "Died"],
                         "n": [412, 168, 97, 54, 23]})
    cases = []
    for box in (Box(20, 60, 440, 200), Box(0, 0, 260, 90)):
        spec = {"ring": donut_rings(data, "route", "n", None)[0]}
        cases.append({"spec": spec, "box": [box.x, box.y, box.width, box.height],
                      "shapes": waffle_drawing(spec, box, fake_measure, DRAWING_STYLE)})
    return {"style": DRAWING_STYLE, "counts": [{"shares": shares, "cells": cell_counts(shares, 100)}
                                               for shares in WAFFLE_SHARES], "cases": cases}


def hexagon_cases() -> dict:
    """Hexagon lattices and counts: a random cloud, points on a regular grid (some as near to an even as to an odd
    row's centre), a faceted shape; and the colour bins for a range of peak counts."""
    generator = np.random.default_rng(11)
    cloud = generator.normal(0, 1, (300, 2)) * [12, 3] + [60, 20]
    even = np.array([[x, y] for x in np.arange(0, 6, 0.5) for y in np.arange(0, 4, 0.25)])
    corners = np.array([[0.0, 0.0], [10.0, 10.0]])
    spacing = hex_grid(corners[:, 0], corners[:, 1], 5, "scatter")
    # Halfway between a centre on an even row and one on the odd row next to it: the even row takes it.
    ties = np.array([[(column + 0.25) * spacing["width"], up * spacing["height"]]
                     for column in range(4) for up in (0.5, 1.5)])
    inputs = [(cloud, 24, [1, 1]), (cloud, 7, [2, 1]), (even, 5, [1, 1]), (even, 3, [2, 3]),
              (np.vstack([corners, ties]), 5, [1, 1])]
    cases = []
    for points, bins, shape in inputs:
        grid = hex_grid(points[:, 0], points[:, 1], bins, "scatter", tuple(shape))
        cells = hex_counts(points[:, 0], points[:, 1], grid)
        cases.append({"x": points[:, 0].tolist(), "y": points[:, 1].tolist(), "bins": bins,
                      "shape": shape, "grid": grid, "cells": cells,
                      "corners": hex_corners(cells[0], grid)})
    return {"cases": cases, "steps": [{"top": top, "steps": count_steps(top)}
                                      for top in (1, 2, 3, 5, 7, 11, 24, 57, 117, 130, 1000)]}


def survival_cases() -> list[dict]:
    generator = np.random.default_rng(7)
    times = np.round(generator.exponential(14, 60), 1)
    events = (generator.uniform(size=60) < 0.7).astype(int)
    inputs = [([1, 2, 2, 3, 4, 5], [1, 1, 0, 1, 0, 1]), ([0, 1, 2], [0, 1, 1]), ([3, 5, 8], [0, 0, 0]), ([4], [1]),
              ([1, 2, 3, 4], [1, 0, 0, 0]), ([2, 2, 2, 5, 5, 9], [1, 1, 0, 1, 1, 0]),
              (times.tolist(), events.tolist())]
    cases = []
    for time, event in inputs:
        table = km_estimate(time, event)
        cases.append({"time": time, "event": event, "median": km_median(table),
                      "table": {column: [None if isinstance(value, float) and math.isnan(value) else value
                                         for value in table[column].tolist()] for column in table.columns}})
    return cases


LOG_RANGES = [(0.25, 1.58), (0.03, 40), (0.5, 2), (0.9, 1.1), (0.001, 0.4), (1, 1), (0.12, 9.5)]


def forest_cases() -> dict:
    use(brand=False)
    data = pd.DataFrame({"study": ["Adams 2019", "Baker 2020", "Chen 2021", "Diaz 2022"],
                         "est": [0.62, 0.81, 0.47, 1.05], "low": [0.41, 0.55, 0.25, 0.70],
                         "high": [0.94, 1.19, 0.88, 1.58], "weight": [31.0, 27.0, 12.0, 30.0],
                         "n": [120, 98, 45, 110]})
    differences = data.assign(est=[-2.1, -0.8, -3.5, 0.6], low=[-3.9, -2.4, -6.8, -1.1], high=[-0.3, 0.8, -0.2, 2.3])
    pooled = {"estimate": 0.72, "low": 0.58, "high": 0.89, "label": "Pooled"}
    specs = [forest_spec(data, "study", "est", "low", "high", weight="weight", columns={"n": "n"}, pooled=pooled,
                         favours=["Favours A", "Favours B"], color="#2474cf"),
             forest_spec(differences, "study", "est", "low", "high", ratio=False, color="#2474cf"),
             forest_spec(data.assign(low=data["est"], high=data["est"]), "study", "est", "low", "high", ratio=False,
                         color="#2474cf", marker="dot", interval=False, null=None)]
    # The last box is too narrow for the columns beside the intervals: they move under each row.
    boxes = [Box(20, 60, 460, 230)] * len(specs) + [Box(20, 60, 240, 260)]
    return {"breaks": [{"low": low, "high": high, "breaks": log_breaks(low, high)} for low, high in LOG_RANGES],
            "cases": [{"spec": spec, "box": [box.x, box.y, box.width, box.height],
                       "shapes": forest_drawing(spec, box, fake_measure, DRAWING_STYLE)}
                      for spec, box in zip([*specs, specs[0]], boxes, strict=True)]}


def density_cases() -> dict:
    generator = np.random.default_rng(11)
    samples = [[1.0, 2.0, 3.0, 4.0, 10.0], np.round(generator.gamma(2.2, 2.0, 60), 1).tolist(),
               np.round(generator.normal(50, 12, 33), 2).tolist(), [3.0, 3.0, 3.0, 4.0], [5.0, 5.0]]
    cases = []
    for values in samples:
        curve = density(values)
        cases.append({"values": values, "bandwidth": bandwidth(values) if len(set(values)) > 1 else None,
                      "quantiles": quantiles(values, [0.25, 0.5, 0.75]),
                      "grid": curve[0] if curve else None, "height": curve[1] if curve else None})
    spans = [[(0, 1), (1, 2), (0, 2)], [(0, 1), (0, 1)], [(0, 3), (1, 2), (2, 3), (0, 1)], [(2, 0)]]
    return {"cases": cases, "jitter": jitter_offsets(12),
            "brackets": [{"spans": span, "levels": bracket_levels(span)} for span in spans]}


def sankey_cases() -> list[dict]:
    use(brand=False)
    data = pd.DataFrame({"source": ["Salary", "Salary", "Salary", "Salary", "Benefits", "Benefits", "Side job"],
                         "account": ["Joint", "Joint", "Savings", "Joint", "Joint", "Savings", "Joint"],
                         "category": ["Rent", "Food", "Reserve", "Leisure", "Food", "Reserve", "Leisure"],
                         "amount": [1200, 450, 400, 250, 150, 100, 200]})
    specs = [sankey_spec(data, ["source", "account", "category"], "amount"),
             sankey_spec(data, ["source", "category"], "amount", color_by="none"),
             sankey_spec(data, ["account", "source", "category"], "amount", color_by="source")]
    box = Box(20, 60, 460, 240)
    return [{"spec": spec, "box": [box.x, box.y, box.width, box.height],
             "shapes": sankey_drawing(spec, box, fake_measure, DRAWING_STYLE)} for spec in specs]


def statistics_cases() -> dict:
    generator = np.random.default_rng(23)
    groups = [np.round(generator.gamma(2.2, 2.0, 30), 1).tolist(), np.round(generator.gamma(3.0, 2.2, 25), 1).tolist()]
    times = np.round(generator.exponential(12, 40), 1).tolist()
    events = (generator.uniform(size=40) < 0.7).astype(int).tolist()
    arms = ["a"] * 14 + ["b"] * 13 + ["c"] * 13
    x = np.round(generator.uniform(0, 10, 30), 2).tolist()
    y = np.round(0.4 * np.array(x) + generator.normal(0, 1, 30), 2).tolist()
    fit = linear_fit(x, y)
    estimate, se = [0.2, 0.35, 0.5, 0.9, 1.3, 0.1], [0.05, 0.1, 0.2, 0.35, 0.5, 0.08]
    return {"rank_sum": {"x": groups[0], "y": groups[1], "p": rank_sum(*groups)},
            "logrank": {"time": times, "event": events, "group": arms, **logrank(times, events, arms)},
            "fit": {"x": x, "y": y, **{key: fit[key] for key in ("slope", "intercept", "slope_se", "t")},
                    "band": [list(values) for values in fit_band(fit, [0.0, 5.0, 10.0])]},
            "pearson": list(pearson(x, y)), "spearman": list(spearman(x, y)),
            "egger": {"estimate": estimate, "se": se, "p": egger(estimate, se)},
            "format_p": [{"value": value, "locale": locale, "text": format_p(value, locale)}
                         for value in (0.0004, 0.001, 0.0123, 0.0999, 0.1, 0.5, 0.999) for locale in ("en", "de")]}


def correlation_cases() -> list[dict]:
    use(brand=False)
    generator = np.random.default_rng(31)
    sofa = generator.uniform(2, 14, 60).round(1)
    data = pd.DataFrame({"sofa": sofa, "lactate": (0.6 + 0.3 * sofa + generator.normal(0, 0.8, 60)).round(2),
                         "age": generator.normal(64, 12, 60).round(),
                         "length_of_stay": (2 + 0.5 * sofa + generator.gamma(2, 1.5, 60)).round(1)})
    cases = []
    for method in ("pearson", "spearman"):
        spec = correlation_spec(data, None, method)
        cases.append({"data": data.to_dict(orient="list"), "method": method, "spec": spec, "box": [20, 60, 440, 240],
                      "shapes": correlation_drawing(spec, Box(20, 60, 440, 240), fake_measure, DRAWING_STYLE)})
    return cases


SURFACE_VIEWS = [None, {"elevation": 60.0, "azimuth": 120.0}, {"elevation": 15.0, "azimuth": -170.0},
                 {"elevation": 45.0, "azimuth": 90.0}]


def surface_data() -> pd.DataFrame:
    """A grid with a gap (a pair without a row) and a missing value."""
    rows = [{"hour": hour, "week": week, "load": round(2 + 3 * math.exp(-((hour - 12) / 3) ** 2) + 0.2 * week, 3)}
            for week in range(1, 6) for hour in range(8, 20, 2)]
    rows = [row for row in rows if (row["hour"], row["week"]) != (14, 2)]
    rows[5]["load"] = float("nan")
    return pd.DataFrame(rows)


def listed(frame: pd.DataFrame) -> dict:
    return {key: [None if pd.isna(value) else value for value in values]
            for key, values in frame.to_dict(orient="list").items()}


ALT_BARS = {
    "units": {"unit": ["ICU", "Ward", "ER", "ICU", "Ward", "ER"],
              "year": ["2024", "2024", "2024", "2025", "2025", "2025"], "n": [10, 30, 20, 12, 31.5, 19]},
    "ties": {"unit": ["a", "b", "c", "d", "e"], "n": [5, 5, 5, 5, 1]},
    "large": {"unit": ["North", "South"], "n": [1.2e9, 3.45e9]},
    "missing": {"unit": ["ICU", "Ward", "ER"], "n": [10, None, 20]},
    "one": {"unit": ["ICU"], "n": [7]},
}
ALT_BAR_OPTIONS = [("units", {}), ("units", {"by": "year"}), ("units", {"by": "year", "stacked": True}),
                   ("units", {"by": "year", "stacked": True, "percent": True}),
                   ("units", {"by": "year", "facet": "year"}), ("units", {"by": "year", "normalize": True}),
                   ("ties", {}), ("large", {}), ("missing", {}), ("one", {}), ("ties", {"title": "Why so even?"})]


def alt_series(units: int, days: bool = True, step: str = "") -> dict:
    """Twelve points per unit, a wave on a rising trend, so start, end and peak differ."""
    rows = [{"t": f"2025-{month:02d}-01{step}" if days else month, "unit": f"Unit {chr(65 + unit)}",
             "v": round(40 + 8 * unit + month + 6 * math.sin(month + unit), 3)}
            for unit in range(units) for month in range(1, 13)]
    return {key: [row[key] for row in rows] for key in ("t", "unit", "v")}


ALT_SERIES = {"three": alt_series(3), "six": alt_series(6), "timed": alt_series(1, step=" 08:30"),
              "numbers": alt_series(2, days=False), "point": {"t": ["2025-01-01"], "unit": ["Unit A"], "v": [4.5]},
              "gap": {"t": ["2025-01-01", "2025-02-01", "2025-01-01"], "unit": ["Unit A", "Unit A", "Unit B"],
                      "v": [3.0, 5.0, None]}}
ALT_SERIES_OPTIONS = [("three", {"by": "unit"}), ("three", {"by": "unit", "window": 3}),
                      ("three", {"summary": ["median", "iqr"]}), ("six", {"by": "unit", "window": 1}),
                      ("timed", {}), ("numbers", {"by": "unit", "window": 2}), ("point", {}),
                      ("gap", {"by": "unit", "window": 1}), ("three", {"by": "unit", "clip": [45, 60]})]


def alt_samples(units: int = 3, years: tuple[str, ...] = ("2024", "2025"), scale: float = 1.0) -> dict:
    """Thirty values per unit and year, spread unevenly, the units' centres apart."""
    rows = [{"unit": f"Unit {chr(65 + unit)}", "year": year,
             "days": round(scale * (2 + 1.5 * unit + year_index + ((index * 7) % 11) / 3), 2)}
            for year_index, year in enumerate(years) for unit in range(units) for index in range(30)]
    return {key: [row[key] for row in rows] for key in ("unit", "year", "days")}


ALT_SAMPLES = {"three": alt_samples(), "one": alt_samples(1, ("2025",)), "shares": alt_samples(scale=0.05),
               "even": {"unit": ["Unit A", "Unit A", "Unit B", "Unit B"], "year": ["2025"] * 4,
                        "days": [2.0, 4.0, 1.0, 5.0]}}
ALT_DISTRIBUTION_OPTIONS = [
    ("spread", "three", {}), ("spread", "three", {"facet": "year"}), ("spread", "three", {"summary": ["mean", "sd"]}),
    ("spread", "three", {"clip": [3, 7], "clip_stats": True}), ("spread", "shares", {"percent": True}),
    ("spread", "one", {}), ("spread", "even", {}), ("raincloud", "three", {}),
    ("raincloud", "three", {"facet": "year"}), ("raincloud", "three", {"summary": ["mean", "ci"]}),
    ("ridgeline", "three", {}),
    ("ridgeline", "three", {"summary": "mean"}), ("ridgeline", "three", {"facet": "year"})]


ALT_SURVIVAL = {
    "two": {"t": [2, 4, 5, 7, 9, 11, 13, 3, 8, 12, 15, 18, 20, 24], "e": [1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0],
            "g": ["ICU"] * 7 + ["Ward"] * 7},
    "half": {"t": [1, 2, 3, 4], "e": [1, 1, 0, 0], "g": ["ICU"] * 4},
    "small": {"t": [0.2, 0.35, 0.5, 0.8, 1.1], "e": [1, 0, 1, 1, 0], "g": ["ICU"] * 5},
}
ALT_SURVIVAL_OPTIONS = [("two", {"by": "g"}), ("two", {"by": "g", "test": False}), ("two", {}),
                        ("two", {"by": "g", "order": ["Ward", "ICU"]}), ("half", {}), ("small", {})]
ALT_EFFECTS = {
    "three": {"study": ["Smith 2019", "Lee 2021", "Kim 2022"], "estimate": [0.55, 1.2, 0.8], "low": [0.3, 0.9, 0.6],
              "high": [1.0, 1.6, 1.05]},
    "ties": {"study": ["A", "B", "C"], "estimate": [1.5, 1.5, 0.9], "low": [1.1, 1.0, 0.7], "high": [2.0, 2.2, 1.2]},
    "one": {"study": ["A"], "estimate": [-0.4], "low": [-0.9], "high": [0.1]},
}
ALT_EFFECT_OPTIONS = [("three", {"pooled": {"estimate": 0.82, "low": 0.7, "high": 0.96}}), ("three", {}),
                      ("three", {"interval": False}), ("three", {"digits": 1}), ("ties", {}),
                      ("one", {"ratio": False})]

ALT_DOTS = {
    "rates": {"unit": ["Medical", "Surgical", "Cardiac", "ICU"], "mortality": [0.13, 0.08, 0.06, 0.13],
              "low": [0.11, 0.07, 0.04, 0.1], "high": [0.15, 0.1, 0.08, 0.16], "n": [1010, 420, 380, 250]},
    "one": {"unit": ["Medical"], "mortality": [0.13], "low": [0.11], "high": [0.15], "n": [1010]},
    # Every third value: ten per unit and year keep the centres apart and the fixture short.
    "samples": {key: values[::3] for key, values in ALT_SAMPLES["three"].items()},
}
ALT_DOT_RATES = {"label": "unit", "estimate": "mortality"}
ALT_DOT_SAMPLES = {"label": "unit", "estimate": "days"}
ALT_DOT_OPTIONS = [("rates", {**ALT_DOT_RATES, "low": "low", "high": "high"}),
                   ("rates", {**ALT_DOT_RATES, "low": "low", "high": "high", "percent": True}),
                   ("rates", {**ALT_DOT_RATES, "n": "n", "digits": 3}), ("one", ALT_DOT_RATES),
                   ("samples", {**ALT_DOT_SAMPLES, "summary": "median", "facet": "year"}),
                   ("samples", {**ALT_DOT_SAMPLES, "summary": ["mean", "ci"]})]
ALT_POINTS = {"x": list(range(1, 16)), "y": [round(2 + 0.5 * x + ((x * 7) % 5) / 2, 2) for x in range(1, 16)],
              "site": [f"Site {chr(65 + index // 3)}" for index in range(15)],
              "group": ["North" if index % 3 else "South" for index in range(15)]}
ALT_POINT_OPTIONS = [{}, {"fit": None}, {"by": "group"}, {"facet": "site"}, {"facet": "site", "fit": None},
                     {"density": True}, {"density": 4, "fit": None}, {"facet": "site", "density": 3}]

ALT_SLICES = {
    "routes": {"route": ["Home", "Rehabilitation", "Ward", "Died"], "patients": [412, 168, 97, 23]},
    "even": {"route": ["Home", "Ward"], "patients": [50, 50]},
    "many": {"route": [f"Route {chr(65 + index)}" for index in range(9)], "patients": [90, 80, 70, 60, 50, 40, 30,
                                                                                         20, 10]},
    "nested": {"unit": ["ICU", "ICU", "Ward", "Ward", "Ward"], "route": ["Home", "Died", "Home", "Rehabilitation",
                                                                         "Died"],
               "patients": [30, 6, 120, 40, 4]},
}
ALT_SLICE_ROUTES = {"label": "route", "value": "patients"}
ALT_SLICE_OPTIONS = [("routes", ALT_SLICE_ROUTES), ("routes", {**ALT_SLICE_ROUTES, "total_label": "patients"}),
                     ("routes", {**ALT_SLICE_ROUTES, "total": False}), ("even", ALT_SLICE_ROUTES),
                     ("many", ALT_SLICE_ROUTES), ("routes", {"label": "route"}),
                     ("nested", {"levels": ["unit", "route"], "value": "patients"})]


ALT_ANSWERS = {"Staffing": [5, 4, 4, 5, 3, 4, 2, 5, 4, 3], "Parking": [2, 3, 4, 1, 2, 5, 3, 2, 4, 1],
               "Food": [1, 2, 2, 3, 1, 4, 2, 1, 3, 2]}


def alt_ratings(items: tuple[str, ...] = ("Staffing", "Parking", "Food"),
                years: tuple[str, ...] = ("2024", "2025")) -> dict:
    """Ten ratings on a five-point scale per item and year, the items' agreement apart; a year later every second
    answer one level higher."""
    rows = [{"item": item, "year": year, "rating": min(5, rating + 1) if year_index and index % 2 else rating}
            for year_index, year in enumerate(years) for item in items
            for index, rating in enumerate(ALT_ANSWERS[item])]
    return {key: [row[key] for row in rows] for key in ("item", "year", "rating")}


ALT_RATINGS = {"three": alt_ratings(), "one": alt_ratings(("Staffing",), ("2025",))}
ALT_RATING_OPTIONS = [("three", {}), ("three", {"facet": "year"}), ("three", {"reverse": ["Food"]}),
                      ("three", {"levels": [1, 2, 3, 4, 5, 6, 7]}), ("three", {"split": 2.5}), ("one", {})]

ALT_FLOWS = {
    "paths": {"origin": ["ER", "ER", "OR", "OR", "Ward"], "unit": ["ICU", "Ward", "ICU", "ICU", "ICU"],
              "outcome": ["Home", "Home", "Rehab", "Home", "Died"], "n": [100, 80, 50, 30, 10]},
    "ties": {"origin": ["ER", "OR", "Ward"], "unit": ["ICU", "ICU", "ICU"], "outcome": ["Home", "Rehab", "Home"],
             "n": [40, 40, 12.5]},
}
ALT_FLOW_OPTIONS = [("paths", {"columns": ["origin", "unit", "outcome"], "value": "n"}),
                    ("paths", {"columns": ["origin", "outcome"], "value": "n"}),
                    ("paths", {"columns": ["origin", "unit", "outcome"], "value": "n", "color_by": "origin"}),
                    ("paths", {"columns": ["origin", "outcome"]}),
                    ("ties", {"columns": ["origin", "unit", "outcome"], "value": "n"})]
ALT_EXCHANGES = {
    "units": {"source": ["ICU", "ICU", "Ward", "ER", "Ward"], "target": ["Ward", "ER", "ER", "ICU", "ICU"],
              "n": [80, 20, 40, 10, 5]},
    "ties": {"source": ["A", "B", "C"], "target": ["B", "C", "A"], "n": [30, 30, 30]},
}
ALT_EXCHANGE_OPTIONS = [("units", {"value": "n"}), ("units", {}), ("ties", {"value": "n"})]
ALT_SETS = {
    "two": {"diabetes": [1, 1, 1, 0, 0, 1, 0, 1], "obesity": [1, 0, 1, 1, 1, 0, 0, 1]},
    "three": {"diabetes": [1, 1, 1, 0, 0, 1, 0, 1], "obesity": [1, 0, 1, 1, 1, 0, 0, 1],
              "smoking": [1, 0, 0, 1, 0, 1, 1, 1]},
}
ALT_SET_OPTIONS = [("two", {"columns": ["diabetes", "obesity"]}),
                   ("three", {"columns": ["diabetes", "obesity", "smoking"]})]

ALT_MEASURES = {"age": [52, 61, 70, 48, 66, 58, 75, 44], "sofa": [3, 5, 9, 4, 6, 4, 8, 2],
                "gcs": [14, 12, 8, 15, 10, 13, 9, 15]}
ALT_MEASURE_OPTIONS = [{}, {"method": "spearman"}, {"columns": ["age", "sofa"]}]
ALT_STUDIES = {"odds": [0.8, 1.1, 0.6, 0.9, 0.75, 0.95], "se": [0.1, 0.2, 0.3, 0.15, 0.25, 0.12],
               "difference": [-1.2, 0.4, -2.1, -0.6, -1.5, -0.3]}
ALT_STUDY_OPTIONS = [{"estimate": "odds", "se": "se"}, {"estimate": "odds", "se": "se", "pooled": 0.9},
                     {"estimate": "difference", "se": "se", "ratio": False}]
ALT_FLOWS_PRISMA = [
    {"identified": 1200, "registers": 30, "duplicates": 230, "screened": 1000, "excluded": 870, "sought": 130,
     "not_retrieved": 10, "assessed": 120, "excluded_reasons": {"Wrong population": 70, "Wrong outcome": 30},
     "included": 20, "reports": 24},
    {"identified": 100, "screened": 100, "included": 5},
    {"identified": 300, "screened": 300, "assessed": 40, "excluded_reasons": {"Wrong design": 32}, "included": 8},
]

ALT_JUDGEMENTS = {
    "wide": {"study": ["Lee 2019", "Kim 2020", "Diaz 2021", "Roy 2022"],
             "Randomisation": ["Low", "High", "Some concerns", "High"], "Blinding": ["low", "some", "low", "high"],
             "Outcome": ["low", "low", "low", "some"]},
    "long": {"study": ["Lee 2019", "Lee 2019", "Kim 2020", "Kim 2020"], "domain": ["D1", "D2", "D1", "D2"],
             "judgement": ["Low risk", "Unclear", "Low", "Moderate"]},
}
ALT_JUDGEMENT_OPTIONS = [("wide", {"domains": ["Randomisation", "Blinding", "Outcome"]}),
                         ("wide", {"domains": ["Randomisation", "Blinding"], "overall": None}),
                         ("wide", {"domains": ["Outcome"], "overall": "All"}),
                         ("long", {"domain": "domain", "judgement": "judgement"}),
                         ("long", {"domain": "domain", "judgement": "judgement", "overall": None})]
ALT_LINKS = {"units": {"source": ["ICU", "Ward", "ICU", "ER"], "target": ["Ward", "ICU", "ER", "Ward"],
                       "n": [50, 30, 20, 60]},
             "ties": {"source": ["A", "B", "C"], "target": ["B", "C", "A"], "n": [2.5, 2.5, 1]}}
ALT_LINK_OPTIONS = [("units", {"value": "n"}), ("units", {}), ("ties", {"value": "n"})]
ALT_SHIFTS = {
    "rooms": {"room": ["OR 1", "OR 1", "OR 2", "OR 3"], "start": [7.25, 12.0, 8.0, 8.0],
              "end": [11.5, 15.0, 13.5, 13.5], "operation": ["Hip", "Knee", "Spine", ""],
              "team": ["Ortho", "Ortho", "Neuro", "Neuro"]},
    "night": {"room": ["Bed 1", "Bed 2"], "start": ["2025-03-01 22:00", "2025-03-01 23:30"],
              "end": ["2025-03-02 01:30", "2025-03-02 06:15"]},
    "one": {"room": ["OR 1"], "start": [7.25], "end": [11.5]},
}
ALT_SHIFT_OPTIONS = [("rooms", {"row": "room"}), ("rooms", {"row": "room", "label": "operation"}),
                     ("rooms", {"row": None, "assign": "first_free", "group": "team"}), ("night", {"row": "room"}),
                     ("one", {"row": "room"})]

ALT_PARTS = {"routes": {"route": ["Home", "Home", "Ward", "Died"], "support": ["Alone", "Family", "Ward", "Died"],
                        "patients": [300, 112, 97, 23]}}
ALT_PART_OPTIONS = [{"levels": ["route", "support"], "value": "patients"}, {"levels": "route", "value": "patients"},
                    {"levels": ["route", "support"]}]
ALT_WAFFLE_OPTIONS = [{"label": "route", "value": "patients"}, {"label": "route"},
                      {"label": "support", "value": "patients", "order": ["Died", "Ward"]}]
ALT_TABLES = {"summary": {"Group": ["ICU", "Ward", "ER"], "n": [12, 30, 7], "Median": [4.5, 3.0, None],
                          "IQR": ["3–6", "2–4", "–"]},
              "one": {"Unit": ["ICU"]}}
ALT_TABLE_OPTIONS = [("summary", {"title": "Admissions"}), ("summary", {"digits": 2}), ("one", {})]
ALT_STAYS = {"beds": {"bed": ["Bed 1", "Bed 1", "Bed 2", "Bed 3"], "unit": ["ICU", "ICU", "ICU", "Ward"],
                      "start": ["2025-03-03 07:00", "2025-03-04 08:00", "2025-03-03 09:00", "2025-03-04 13:00"],
                      "end": ["2025-03-03 12:00", "2025-03-04 10:00", "2025-03-03 10:30", "2025-03-04 18:45"]}}
ALT_STAY_OPTIONS = [{}, {"value": "count"}, {"group": "unit"}, {"bin": 30}]


def alt_text_cases() -> dict:
    """Every chart that describes its data, with its alt text, in English and German, for both packages to write
    alike."""
    import matplotlib.pyplot as plt

    import hairline as hl
    from hairline.export import figure_alt

    def case(locale: str, data: dict, options: dict, draw) -> dict:
        hl.use(brand=False, locale=locale)
        frame = pd.DataFrame({key: [np.nan if value is None else value for value in values]
                              for key, values in data.items()})
        figure = draw(frame, options)
        plt.close(figure.figure)
        return {"locale": locale, "data": data, "options": options, "alt": figure_alt(figure)}
    bars = [case(locale, ALT_BARS[name], options, lambda frame, options: hl.bars(frame, "unit", "n", **options))
            for locale in ("en", "de") for name, options in ALT_BAR_OPTIONS]
    share = {**ALT_SERIES["three"], "v": [value / 100 for value in ALT_SERIES["three"]["v"]]}
    series = [case(locale, ALT_SERIES[name], options,
                   lambda frame, options: hl.timeseries(frame, "t", "v", **options))
              for locale in ("en", "de") for name, options in ALT_SERIES_OPTIONS]
    series.append(case("de", share, {"by": "unit", "percent": True},
                       lambda frame, options: hl.timeseries(frame, "t", "v", **options)))
    charts = {"spread": hl.spread, "raincloud": hl.raincloud, "ridgeline": hl.ridgeline}
    distributions = [{"chart": chart, **case(locale, ALT_SAMPLES[name], options,
                                             lambda frame, options, chart=chart: charts[chart](frame, "unit", "days",
                                                                                                **options))}
                     for locale in ("en", "de") for chart, name, options in ALT_DISTRIBUTION_OPTIONS]
    survival = [case(locale, ALT_SURVIVAL[name], options,
                     lambda frame, options: hl.kaplan_meier(frame, "t", "e", **options))
                for locale in ("en", "de") for name, options in ALT_SURVIVAL_OPTIONS]
    effects = [case(locale, ALT_EFFECTS[name], options, lambda frame, options: hl.forest(frame, **options))
               for locale in ("en", "de") for name, options in ALT_EFFECT_OPTIONS]
    dots = [case(locale, ALT_DOTS[name], options, lambda frame, options: hl.dotplot(frame, **options))
            for locale in ("en", "de") for name, options in ALT_DOT_OPTIONS]
    points = [case(locale, ALT_POINTS, options, lambda frame, options: hl.scatter(frame, "x", "y", **options))
              for locale in ("en", "de") for options in ALT_POINT_OPTIONS]
    slices = [case(locale, ALT_SLICES[name], options, lambda frame, options: hl.donut(frame, **options))
              for locale in ("en", "de") for name, options in ALT_SLICE_OPTIONS]
    ratings = [case(locale, ALT_RATINGS[name], options,
                    lambda frame, options: hl.likert(frame, "item", "rating", **options))
               for locale in ("en", "de") for name, options in ALT_RATING_OPTIONS]
    flows = [case(locale, ALT_FLOWS[name], options, lambda frame, options: hl.sankey(frame, **options))
             for locale in ("en", "de") for name, options in ALT_FLOW_OPTIONS]
    exchanges = [case(locale, ALT_EXCHANGES[name], options,
                      lambda frame, options: hl.chord(frame, "source", "target", **options))
                 for locale in ("en", "de") for name, options in ALT_EXCHANGE_OPTIONS]
    sets = [case(locale, ALT_SETS[name], options, lambda frame, options: hl.venn(frame, **options))
            for locale in ("en", "de") for name, options in ALT_SET_OPTIONS]
    measures = [case(locale, ALT_MEASURES, options, lambda frame, options: hl.correlation(frame, **options))
                for locale in ("en", "de") for options in ALT_MEASURE_OPTIONS]
    studies = [case(locale, ALT_STUDIES, options, lambda frame, options: hl.funnel(frame, **options))
               for locale in ("en", "de") for options in ALT_STUDY_OPTIONS]
    judgements = [case(locale, ALT_JUDGEMENTS[name], options,
                       lambda frame, options: hl.risk_of_bias(frame, "study", **options))
                  for locale in ("en", "de") for name, options in ALT_JUDGEMENT_OPTIONS]
    links = [case(locale, ALT_LINKS[name], options, lambda frame, options: hl.arcs(frame, "source", "target",
                                                                                     **options))
             for locale in ("en", "de") for name, options in ALT_LINK_OPTIONS]
    shifts = [case(locale, ALT_SHIFTS[name], options,
                   lambda frame, options: hl.swimlanes(frame, start="start", end="end", **options))
              for locale in ("en", "de") for name, options in ALT_SHIFT_OPTIONS]
    parts = [case(locale, ALT_PARTS["routes"], options, lambda frame, options: hl.partition(frame, **options))
             for locale in ("en", "de") for options in ALT_PART_OPTIONS]
    waffles = [case(locale, ALT_PARTS["routes"], options, lambda frame, options: hl.waffle(frame, **options))
               for locale in ("en", "de") for options in ALT_WAFFLE_OPTIONS]
    tables = [case(locale, ALT_TABLES[name], options, lambda frame, options: hl.table(frame, **options))
              for locale in ("en", "de") for name, options in ALT_TABLE_OPTIONS]
    stays = [case(locale, ALT_STAYS["beds"], options,
                  lambda frame, options: hl.lanes(frame, "bed", "start", "end", **options))
             for locale in ("en", "de") for options in ALT_STAY_OPTIONS]
    reviews = []
    for locale in ("en", "de"):
        hl.use(brand=False, locale=locale)
        for counts in ALT_FLOWS_PRISMA:
            figure = hl.prisma(counts)
            plt.close(figure.figure)
            reviews.append({"locale": locale, "counts": counts, "alt": figure_alt(figure)})
    hl.use(brand=False)
    return {"bars": bars, "timeseries": series, "distributions": distributions, "kaplan_meier": survival,
            "forest": effects, "dotplot": dots, "scatter": points, "donut": slices, "likert": ratings,
            "sankey": flows, "chord": exchanges, "venn": sets, "correlation": measures, "funnel": studies,
            "prisma": reviews, "risk_of_bias": judgements, "arcs": links, "swimlanes": shifts,
            "partition": parts, "table": tables, "lanes": stays, "waffle": waffles}


def heatmap_cases() -> dict:
    """The surface's grid as a heatmap (numbers and shares, bands and gradient, with marginal means or sums), in a
    box and at a given height; and the surface with its heatmap beside it."""
    use(brand=False)
    data, titles, box = surface_data(), {"x": "Hour", "y": "Week", "z": "Load"}, [20, 60, 440, 300]
    cases = []
    for percent, gradient, height, margins in ((False, False, None, None), (True, True, None, None),
                                               (False, True, 180.0, None), (True, False, None, "mean"),
                                               (False, False, 180.0, "sum")):
        frame = data.assign(load=data["load"] / 10) if percent else data
        spec = heatmap_spec(frame, "hour", "week", "load", titles=titles, percent=percent, gradient=gradient,
                            margins=margins)
        shapes, cells = heatmap_layout(heatmap_scene(spec, fake_measure, DRAWING_STYLE), Box(*box), height)
        cases.append({"data": listed(frame), "percent": percent, "gradient": gradient, "height": height,
                      "margins": margins, "titles": titles, "box": box, "spec": spec, "shapes": shapes,
                      "cells": cells})
    spec = surface_spec(data, "hour", "week", "load", titles=titles, heatmap=True)
    layout = pair_layout(surface_scene(spec, fake_measure, DRAWING_STYLE),
                         heatmap_scene(spec["flat"], fake_measure, DRAWING_STYLE), Box(*box))
    pair = {"data": listed(data), "titles": titles, "box": box, "spec": spec, "shapes": layout["shapes"],
            "cells": layout["cells"], "surface_box": [layout["box"].x, layout["box"].y, layout["box"].width,
                                                      layout["box"].height]}
    return {"cases": cases, "pair": pair}


def surface_cases() -> list[dict]:
    """A grid with a gap (a pair without a row) and a missing value, as numbers and as shares, in bands from four
    views and blended along the ramp from two."""
    use(brand=False)
    rows = [{"hour": hour, "week": week, "load": round(2 + 3 * math.exp(-((hour - 12) / 3) ** 2) + 0.2 * week, 3)}
            for week in range(1, 6) for hour in range(8, 20, 2)]
    rows = [row for row in rows if (row["hour"], row["week"]) != (14, 2)]
    rows[5]["load"] = float("nan")
    data = pd.DataFrame(rows)
    cases = []
    for percent, gradient in ((False, False), (True, False), (False, True), (True, True)):
        frame = data.assign(load=data["load"] / 10) if percent else data
        titles = {"x": "Hour", "y": "Week", "z": "Load"}
        spec = surface_spec(frame, "hour", "week", "load", titles=titles, percent=percent, gradient=gradient)
        scene = surface_scene(spec, fake_measure, DRAWING_STYLE)
        for view in SURFACE_VIEWS[:2] if gradient else SURFACE_VIEWS:
            columns = {key: [None if pd.isna(value) else value for value in values]
                       for key, values in frame.to_dict(orient="list").items()}
            cases.append({"data": columns, "percent": percent, "gradient": gradient,
                          "titles": titles, "view": view, "spec": spec, "scene": scene, "box": [20, 60, 440, 300],
                          "shapes": scene_shapes(scene, Box(20, 60, 440, 300), view)})
    return cases


def meta_review_cases() -> dict:
    use(brand=False)
    trials = pd.DataFrame({"or": [0.62, 0.81, 0.47, 1.05, 0.69, 0.4, 0.55, 0.9],
                           "se": [0.21, 0.19, 0.32, 0.2, 0.3, 0.45, 0.38, 0.15]})
    differences = pd.DataFrame({"md": [-2.1, -0.8, -3.5, 0.6, -1.2], "se": [0.9, 0.7, 1.4, 0.8, 1.1]})
    box = Box(20, 60, 440, 240)
    funnels = []
    for data, estimate, ratio in ((trials, "or", True), (differences, "md", False)):
        spec = funnel_spec(data, estimate, "se", ratio=ratio)
        funnels.append({"data": data.to_dict(orient="list"), "estimate": estimate, "ratio": ratio, "spec": spec,
                        "shapes": funnel_drawing(spec, box, fake_measure, DRAWING_STYLE)})
    wide = pd.DataFrame({"study": list("ABCDEF"), "Randomisation": ["Low", "Low", "Some", "High", "Low", "Low"],
                         "Missing data": ["Low", "High", "Low", "Low", "Some concerns", "Low"],
                         "Measurement": ["low risk", "Low", "Low", "Unclear", "Low", "Serious"]})
    spec = risk_of_bias_spec(wide, "study", domains=["Randomisation", "Missing data", "Measurement"])
    return {"box": [box.x, box.y, box.width, box.height], "funnels": funnels,
            "risk_of_bias": {"data": wide.to_dict(orient="list"), "spec": spec,
                             "shapes": risk_of_bias_drawing(spec, box, fake_measure, DRAWING_STYLE)}}


PRISMA_COUNTS = {"identified": 1240, "registers": 85, "duplicates": 260, "automation": 45, "screened": 1020,
                 "excluded": 900, "sought": 120, "not_retrieved": 10, "assessed": 110,
                 "excluded_reasons": {"Wrong population": 40, "Wrong intervention": 31, "No control group": 21},
                 "included": 18, "reports": 22}


def flow_cases() -> dict:
    use(brand=False)
    box = Box(20, 60, 440, 400)
    transfers = pd.DataFrame({"origin": ["ED", "ED", "ED", "Ward", "ICU", "ICU", "Ward", "Theatre"],
                              "destination": ["ICU", "Ward", "ICU", "ICU", "Ward", "Home", "Home", "ICU"]})
    crowded = pd.DataFrame({"origin": [f"Department of medicine {index}" for index in range(8)],
                            "destination": [f"Department of medicine {(index + 3) % 8}" for index in range(8)]})
    arc_specs = [arcs_spec(transfers, "origin", "destination", None), arcs_spec(crowded, "origin", "destination", None)]
    referrals = pd.DataFrame({"origin": ["ED", "ED", "Ward", "Ward", "ICU", "ED", "Theatre", "ICU"],
                              "destination": ["ICU", "Ward", "ICU", "ED", "Ward", "ICU", "ICU", "Theatre"],
                              "patients": [40, 25, 18, 6, 22, 10, 30, 12]})
    chord = chord_spec(referrals, "origin", "destination", "patients")
    conditions = {"Diabetes": ["a", "b", "c", "d", "e"], "Hypertension": ["c", "d", "e", "f"],
                  "Obesity": ["e", "f", "g"]}
    screening = {"Screened": list(range(24)), "Confirmed": list(range(18, 30))}
    venns = [venn_spec(conditions), venn_spec(screening, proportional=True)]
    prisma = prisma_spec(PRISMA_COUNTS)
    return {"box": [box.x, box.y, box.width, box.height], "prisma": {"counts": PRISMA_COUNTS, "spec": prisma,
            "shapes": prisma_drawing(prisma, box, fake_measure, DRAWING_STYLE)},
            "chord": {"data": referrals.to_dict(orient="list"), "spec": chord,
                      "shapes": chord_drawing(chord, box, fake_measure, DRAWING_STYLE)},
            "venn": [{"sets": sets, "proportional": spec["proportional"], "spec": spec,
                      "shapes": venn_drawing(spec, box, fake_measure, DRAWING_STYLE)}
                     for sets, spec in zip([conditions, screening], venns, strict=True)],
            "arcs": [{"data": data.to_dict(orient="list"), "spec": spec,
                      "shapes": arcs_drawing(spec, box, fake_measure, DRAWING_STYLE)}
                     for data, spec in zip((transfers, crowded), arc_specs, strict=True)]}


LONG_LABEL = "An exceptionally long category label that keeps going for seventy chars"


def drawn(chart: str, spec: dict, box: Box, draw) -> dict:
    """A narrow-box case: the shapes, or the layout error's message."""
    case = {"chart": chart, "spec": spec, "box": [box.x, box.y, box.width, box.height]}
    try:
        return {**case, "shapes": draw(spec, box, fake_measure, DRAWING_STYLE)}
    except HairlineLayoutError as error:
        return {**case, "error": str(error)}


def wrapping_cases() -> dict:
    """Labels that meet the edge of their room in every chart: wrapped into the room a chart's minimum size leaves,
    refused with the room needed, or running on below a panel too short for them."""
    use(brand=False)
    single = pd.DataFrame({"name": [LONG_LABEL, "Home", "Care home", "Rehabilitation"], "n": [40, 30, 20, 10]})
    nested = pd.DataFrame({"route": ["Home"] * 3 + ["Rehabilitation"] * 3,
                           "detail": ["Alone with daily visits from the district nursing team", "With support",
                                      "Other", "Inpatient", "Outpatient", "Day clinic"], "n": [25, 16, 4, 12, 5, 3]})
    many = pd.DataFrame({"parent": [f"Parent {index // 6}" for index in range(12)],
                         "child": [f"Child {index}" for index in range(12)],
                         "n": [1 + index % 5 for index in range(12)]})
    donuts = [(single, "name", None, "outside", Box(0, 0, 200, 150), None),
              (single, "name", None, "outside", Box(0, 0, 90, 150), None),
              (nested, None, ["route", "detail"], "key", Box(0, 0, 300, 160), None),
              (many, None, ["parent", "child"], "key", Box(0, 0, 400, 80), None),
              (single.iloc[1:], "name", None, "ring", Box(0, 0, 140, 140), "patients discharged home in 2025")]
    cases = []
    for data, label, levels, mode, box, total_label in donuts:
        spec = {"rings": donut_rings(data, label, "n", levels), "labels": mode, "total": "731",
                "total_label": total_label}
        cases.append(drawn("donut", spec, box, donut_drawing))
    referrals = pd.DataFrame({"origin": [LONG_LABEL, "ED", "Ward"], "destination": ["ICU", "Ward", LONG_LABEL],
                              "patients": [4, 5, 6]})
    cases.append(drawn("chord", chord_spec(referrals, "origin", "destination", "patients"), Box(0, 0, 210, 200),
                       chord_drawing))
    for sets, box in (({LONG_LABEL: [1, 2, 3], "Hypertension": [2, 3, 4]}, Box(0, 0, 200, 60)),
                      ({"Diabetes": [1, 2], "Hypertension": [2, 3], "Obesity": [3, 4]}, Box(0, 0, 300, 50)),
                      ({"Supercalifragilisticexpialidocious": [1, 2], "B": [2, 3]}, Box(0, 0, 120, 200))):
        cases.append(drawn("venn", venn_spec(sets), box, venn_drawing))
    wide = pd.DataFrame({"study": list("ABC"), LONG_LABEL: ["Low", "High", "Low"], "Missing": ["Low", "Low", "Some"]})
    spec = risk_of_bias_spec(wide, "study", domains=[LONG_LABEL, "Missing"],
                             overall="Overall judgement across every domain")
    cases.append(drawn("risk_of_bias", spec, Box(0, 0, 200, 200), risk_of_bias_drawing))
    trials = pd.DataFrame({"study": ["Adams 2019", "Baker 2020"], "est": [0.62, 1.05], "low": [0.41, 0.70],
                           "high": [0.94, 1.58]})
    spec = forest_spec(trials, "study", "est", "low", "high", color="#2474cf",
                       favours=["Favours the experimental treatment arm", "Favours the usual care control arm"])
    cases.append(drawn("forest", spec, Box(20, 60, 240, 260), forest_drawing))
    budget = pd.DataFrame({"source": ["Salary", "Salary", "Benefits"], "account": ["Joint", LONG_LABEL, "Joint"],
                           "category": ["Rent", LONG_LABEL, "Food"], "amount": [5, 3, 2]})
    sources = pd.DataFrame({"source": [f"Source {index}" for index in range(8) for _ in range(2)],
                            "category": ["Rent", "Food"] * 8, "amount": [1 + index % 4 for index in range(16)]})
    for spec, box in ((sankey_spec(budget, ["source", "category"], "amount"), Box(0, 0, 260, 160)),
                      (sankey_spec(budget, ["source", "account", "category"], "amount"), Box(0, 0, 460, 200)),
                      (sankey_spec(sources, ["source", "category"], "amount"), Box(0, 0, 300, 80)),
                      (sankey_spec(budget, ["source", "category"], "amount"), Box(0, 0, 90, 160))):
        cases.append(drawn("sankey", spec, box, sankey_drawing))
    blocks = [([10.0, 12.0, 30.0], [5.0, 10.0, 5.0], 0.0, 100.0), ([50.0, 50.0], [20.0, 20.0], 0.0, 30.0),
              ([90.0, 5.0, 40.0], [8.0, 16.0, 8.0], 0.0, 100.0), ([], [], 0.0, 10.0)]
    return {"style": DRAWING_STYLE, "cases": cases,
            "blocks": [{"positions": positions, "heights": heights, "top": top, "bottom": bottom,
                        "centres": spread_blocks(positions, heights, top, bottom)}
                       for positions, heights, top, bottom in blocks]}

def chart_colour_cases() -> list[dict]:
    daylight = load_tokens()["palettes"]["daylight"]
    inputs = [({}, {}, {}, ["Female", "Male"]), ({}, {"Surgical": daylight[0]}, {}, ["Female", "Male"]),
              ({}, {"A": daylight[0], "X": daylight[0]}, {}, ["A", "X"]),
              ({"F": "#000000"}, {"R": daylight[1]}, {"O": "#ffffff"}, ["O", "F", "R", "N1", "N2"]),
              ({"Control": daylight[0]}, {"Arm A": daylight[2]}, {}, ["Arm A", "Arm B", "Control"])]
    return [{"palette": daylight, "fixed": fixed, "remembered": remembered, "override": override, "names": names,
             "expected": chart_colors(daylight, "palette 'daylight'", fixed, remembered, override, names)}
            for fixed, remembered, override, names in inputs]



def swatch_cases() -> dict:
    """Colour sets as swatch rows: every set, and a pick across all four kinds in a narrower box."""
    use(brand=False)
    cases = []
    for names, box in ((None, Box(20, 60, 440, 300)), (["calm", "ink", "greys", "teal-berry"], Box(10, 40, 260, 200))):
        rows = swatch_rows(names)
        cases.append({"names": names, "box": [box.x, box.y, box.width, box.height], "rows": rows,
                      "shapes": swatches_drawing({"rows": rows}, box, fake_measure, DRAWING_STYLE)})
    return {"style": DRAWING_STYLE, "cases": cases}


EXPLICIT_RAMPS_BRAND = """meta:
  name: Ramp test
color:
  palette:
    harbor: "#0b3d6e"
    poppy: "#f2545b"
    glacier: "#8cc8ff"
    fern: "#7fd8a0"
defaults:
  hairline:
    categorical: [harbor, poppy, glacier, fern]
    sequential: poppy
    diverging: [glacier, fern]
"""


def brand_ramp_cases() -> dict:
    """The ramp rule on a few hues, and the ramps of the example brand and of a brand that names its hues."""
    import tempfile
    rule = {"sequential": [{"hue": hue, "colors": sequential_ramp(hue)} for hue in (30.0, 140.0, 290.0, None)],
            "diverging": [{"hues": [250.0, 40.0], "colors": diverging_ramp(250.0, 40.0)}]}
    example = use(brand=REPO / "brands" / "example" / "_brand.yml").ramps
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "_brand.yml"
        path.write_text(EXPLICIT_RAMPS_BRAND, encoding="utf-8")
        explicit = use(brand=path).ramps
    use(brand=False)
    return {"rule": rule, "example": {name: list(colors) for name, colors in example.items()},
            "explicit_yaml": EXPLICIT_RAMPS_BRAND,
            "explicit": {name: list(colors) for name, colors in explicit.items()}}


def weight_cases() -> list[dict]:
    """Requested weights against the faces a family has: the face that is drawn instead of a missing weight."""
    families = [[400, 700], [400, 500, 600], [100, 300, 400, 500, 700, 900], [400], [300, 700], [600, 800], [],
                [450, 700]]
    return [{"requested": requested, "available": available, "result": nearest_weight(requested, available)}
            for available in families for requested in (100, 300, 400, 450, 500, 600, 700, 900)]


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
    write("chart_colours.json", chart_colour_cases())
    write("points.json", point_cases())
    write("chart_helpers.json", chart_helper_cases())
    write("donut.json", {"style": DRAWING_STYLE, "cases": donut_cases()})
    write("survival.json", survival_cases())
    write("density.json", density_cases())
    write("statistics.json", statistics_cases())
    write("flows.json", {"style": DRAWING_STYLE, **flow_cases()})
    write("meta_review.json", {"style": DRAWING_STYLE, **meta_review_cases()})
    write("correlation.json", {"style": DRAWING_STYLE, "cases": correlation_cases()})
    write("surface.json", {"style": DRAWING_STYLE, "cases": surface_cases()})
    write("heatmap.json", {"style": DRAWING_STYLE, **heatmap_cases()})
    write("alt_text.json", alt_text_cases())
    write("sankey.json", {"style": DRAWING_STYLE, "cases": sankey_cases()})
    write("forest.json", {"style": DRAWING_STYLE, **forest_cases()})
    write("partition.json", {"style": DRAWING_STYLE, "cases": partition_cases()})
    write("waffle.json", waffle_cases())
    write("hexagons.json", hexagon_cases())
    write("study.json", study_cases())
    write("spread.json", spread_cases(DRAWING_STYLE, fake_measure))
    write("swatches.json", swatch_cases())
    write("brand_ramps.json", brand_ramp_cases())
    write("weights.json", weight_cases())
    write("wrapping.json", wrapping_cases())
    return 0


if __name__ == "__main__":
    sys.exit(main())
