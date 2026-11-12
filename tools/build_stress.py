"""Write tokens/fixtures/stress.json: hard inputs for every chart, which both packages draw and check with
check_layout() / hl_check_layout(). Each case names the chart, the size preset, the data (columns of values) and
the arguments; the data is invented and fixed by a seed, so both languages draw the same figure.

Run from python/: uv run python ../tools/build_stress.py, then ../tools/sync_tokens.py."""

from __future__ import annotations

import json
import string
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[1] / "tokens" / "fixtures" / "stress.json"
LETTERS = string.ascii_uppercase
LONG = "with a longer descriptive name"


def labels(count: int, long_every: int = 3) -> list[str]:
    """Item names; every `long_every`-th is long, so short and long labels share one axis."""
    return [f"Item {LETTERS[index % 26]}{index // 26 or ''} {LONG}" if index % long_every == 0
            else f"Item {LETTERS[index % 26]}{index // 26 or ''}" for index in range(count)]


def rounded(values) -> list[float]:
    return [round(float(value), 2) for value in values]


def skewed(rng, groups: list[str], sizes: list[int], centres: list[float]) -> dict:
    group, value = [], []
    for name, size, centre in zip(groups, sizes, centres, strict=True):
        group += [name] * size
        value += rounded(rng.lognormal(np.log(centre), 0.3, size))
    return {"group": group, "value": value}


def distribution_cases(rng) -> list[dict]:
    bands = ["Band A", "Band B", "Band C", "Band D"]
    outlier = skewed(rng, bands, [70, 75, 36, 20], [9, 11, 16, 28])
    outlier["group"].append("Band C")
    outlier["value"].append(51.0)
    many = skewed(rng, labels(14), [30] * 14, list(np.linspace(10, 40, 14)))
    dense = skewed(rng, ["Group 1", "Group 2"], [400, 400], [20, 24])
    return [
        {"name": "raincloud_outlier", "chart": "raincloud", "size": "single", "data": outlier,
         "args": {"group": "group", "value": "value", "y_title": "Score (units)"}},
        {"name": "raincloud_dense", "chart": "raincloud", "size": "onehalf", "data": dense,
         "args": {"group": "group", "value": "value"}},
        {"name": "raincloud_many", "chart": "raincloud", "size": "single", "data": many,
         "args": {"group": "group", "value": "value"}},
        {"name": "spread_many", "chart": "spread", "size": "single", "data": many,
         "args": {"group": "group", "value": "value", "show_n": True}},
        {"name": "ridgeline_many", "chart": "ridgeline", "size": "single", "data": many,
         "args": {"group": "group", "value": "value", "reference": {"Target": 30}}},
        {"name": "scatter_edge", "chart": "scatter", "size": "single",
         "data": {"x": rounded(rng.uniform(0, 50, 80)) + [50.9], "y": rounded(rng.uniform(0, 10, 80)) + [10.2]},
         "args": {"x": "x", "y": "y"}},
    ]


def bar_cases(rng) -> list[dict]:
    periods = [f"P{index + 1:02d}" for index in range(29)]
    items = labels(25)
    return [
        {"name": "bars_many_categories", "chart": "bars", "size": "onehalf",
         "data": {"period": periods, "count": [int(value) for value in rng.integers(0, 12, 29)]},
         "args": {"category": "period", "value": "count", "order": periods, "x_title": "Period",
                  "y_title": "Events"}},
        {"name": "bars_long_labels", "chart": "bars", "size": "single",
         "data": {"item": items, "count": [int(value) for value in rng.choice([0, 1, 2, 3, 5, 8, 12, 90, 110], 25)]},
         "args": {"category": "item", "value": "count", "order": items, "x_title": "Rows"}},
        {"name": "bars_stacked_series", "chart": "bars", "size": "single",
         "data": {"year": [str(year) for year in range(2015, 2027) for _ in range(6)],
                  "kind": [f"Kind {index + 1} {LONG}" for _ in range(12) for index in range(6)],
                  "count": [int(value) for value in rng.integers(1, 40, 72)]},
         "args": {"category": "year", "value": "count", "by": "kind", "stacked": True}},
    ]


def row_cases(rng) -> list[dict]:
    items = labels(25)
    estimates = rng.uniform(0.05, 0.4, 25)
    statements = labels(12, 2)
    return [
        {"name": "dotplot_long", "chart": "dotplot", "size": "single",
         "data": {"unit": items, "rate": rounded(estimates), "low": rounded(estimates - 0.04),
                  "high": rounded(estimates + 0.05)},
         "args": {"label": "unit", "estimate": "rate", "low": "low", "high": "high", "percent": True}},
        {"name": "likert_long", "chart": "likert", "size": "single",
         "data": {"statement": [name for name in statements for _ in range(40)],
                  "rating": [int(value) for value in rng.integers(1, 6, 480)]},
         "args": {"item": "statement", "rating": "rating"}},
        {"name": "forest_long", "chart": "forest", "size": "single",
         "data": {"study": [f"Study {index + 1} {LONG}" for index in range(15)],
                  "or": rounded(np.exp(rng.normal(-0.2, 0.3, 15))),
                  "low": rounded(np.exp(rng.normal(-0.2, 0.3, 15)) * 0.6),
                  "high": rounded(np.exp(rng.normal(-0.2, 0.3, 15)) * 1.6 + 0.6)},
         "args": {"study": "study", "estimate": "or", "low": "low", "high": "high"}},
    ]


def time_cases(rng) -> list[dict]:
    days = [f"2025-{month:02d}-{day:02d}" for month in range(1, 13) for day in (1, 15)]
    series = [f"Series {index + 1} {LONG}" for index in range(6)]
    months = rounded(rng.exponential(20, 120))
    return [
        {"name": "timeseries_panels", "chart": "timeseries", "size": "single",
         "data": {"day": days * 6, "series": [name for name in series for _ in days],
                  "value": rounded(rng.normal(50, 10, len(days) * 6))},
         "args": {"x": "day", "y": "value", "by": "series"}},
        {"name": "kaplan_meier_end", "chart": "kaplan_meier", "size": "single",
         "data": {"arm": [f"Arm {index % 3 + 1} {LONG}" for index in range(120)],
                  "months": [min(value, 60.0) for value in months],
                  "died": [int(value) for value in rng.integers(0, 2, 120)]},
         "args": {"time": "months", "event": "died", "by": "arm"}},
    ]


def drawn_cases(rng) -> list[dict]:
    nodes = labels(9, 2)
    origin = [nodes[index] for index in rng.integers(0, 9, 300)]
    destination = [nodes[index] for index in rng.integers(0, 9, 300)]
    pairs = [(first, second) for first, second in zip(origin, destination, strict=True) if first != second]
    routes = labels(10, 2)
    shares = [int(value) for value in rng.integers(1, 200, 10)] + [1]
    return [
        {"name": "donut_many", "chart": "donut", "size": "single",
         "data": {"route": routes + ["Item rare"], "patients": shares},
         "args": {"label": "route", "value": "patients"}},
        {"name": "arcs_many", "chart": "arcs", "size": "single",
         "data": {"origin": [first for first, _ in pairs], "destination": [second for _, second in pairs]},
         "args": {"source": "origin", "target": "destination"}},
        {"name": "chord_many", "chart": "chord", "size": "single",
         "data": {"origin": [first for first, _ in pairs], "destination": [second for _, second in pairs]},
         "args": {"source": "origin", "target": "destination"}},
        {"name": "correlation_many", "chart": "correlation", "size": "single",
         "data": {f"Measure {index + 1} {LONG}": rounded(rng.normal(0, 1, 60)) for index in range(10)},
         "args": {}},
    ]


def summary_cases(rng) -> list[dict]:
    """summary= marks and stats= numbers on every chart that draws them, close to the smallest size."""
    four = skewed(rng, ["Band A", "Band B", "Band C", "Band D"], [40, 35, 30, 25], [9, 12, 16, 22])
    eight = skewed(rng, [f"Band {letter}" for letter in "ABCDEFGH"], [20] * 8, list(np.linspace(8, 30, 8)))
    units = labels(12)
    days = [f"2025-03-{day:02d}" for day in range(1, 29)]
    return [
        {"name": "raincloud_summary", "chart": "raincloud", "size": "single", "data": four,
         "args": {"group": "group", "value": "value", "summary": ["median", "mean", "iqr", "range"],
                  "stats": ["median", "iqr", "mean", "range"]}},
        {"name": "raincloud_stats_many", "chart": "raincloud", "size": "single", "data": eight,
         "args": {"group": "group", "value": "value", "summary": ["mean", "ci"], "stats": ["mean", "ci"]}},
        {"name": "spread_summary", "chart": "spread", "size": "single", "data": eight,
         "args": {"group": "group", "value": "value", "summary": ["mean", "ci", "range"],
                  "stats": ["mean", "sd", "ci", "n"]}},
        {"name": "ridgeline_stats", "chart": "ridgeline", "size": "single", "data": eight,
         "args": {"group": "group", "value": "value", "summary": ["median", "mean"], "stats": ["median", "iqr", "n"]}},
        {"name": "dotplot_summary", "chart": "dotplot", "size": "single",
         "data": {"unit": [name for name in units for _ in range(15)],
                  "stay": rounded(rng.lognormal(1.6, 0.5, 180))},
         "args": {"label": "unit", "estimate": "stay", "summary": ["mean", "ci"]}},
        {"name": "timeseries_summary", "chart": "timeseries", "size": "single",
         "data": {"day": [day for day in days for _ in range(10)],
                  "ward": [f"Ward {index % 2 + 1} {LONG}" for index in range(280)],
                  "score": rounded(rng.normal(50, 8, 280))},
         "args": {"x": "day", "y": "score", "by": "ward", "summary": ["median", "iqr"],
                  "stats": ["median", "iqr", "n"]}},
    ]


def comparison_cases(rng) -> list[dict]:
    """compare= on every chart that writes it, and numbers= beside the rows, close to the smallest size."""
    six = skewed(rng, [f"Group {index + 1} {LONG}" if index % 2 else f"Group {index + 1}" for index in range(6)],
                 [30, 25, 40, 18, 35, 22], [10, 11, 14, 9, 18, 12])
    three = skewed(rng, ["Arm A", "Arm B", "Arm C"], [40, 38, 41], [10, 12, 15])
    return [
        {"name": "spread_compare", "chart": "spread", "size": "single", "data": six,
         "args": {"group": "group", "value": "value", "compare": "Group 1", "stats": ["median", "n"]}},
        {"name": "spread_numbers_right", "chart": "spread", "size": "double", "data": six,
         "args": {"group": "group", "value": "value", "compare": "adjacent", "stats": ["median"],
                  "numbers": "right"}},
        {"name": "raincloud_compare", "chart": "raincloud", "size": "single", "data": three,
         "args": {"group": "group", "value": "value", "compare": "adjacent"}},
        {"name": "ridgeline_compare", "chart": "ridgeline", "size": "onehalf", "data": six,
         "args": {"group": "group", "value": "value", "compare": "Group 1"}},
        {"name": "dotplot_compare", "chart": "dotplot", "size": "single", "data": six,
         "args": {"label": "group", "estimate": "value", "summary": ["mean", "ci"], "compare": "Group 1",
                  "numbers": "below"}},
    ]


def main() -> None:
    rng = np.random.default_rng(20261111)
    cases = distribution_cases(rng) + bar_cases(rng) + row_cases(rng) + time_cases(rng) + drawn_cases(rng) + \
        summary_cases(rng) + comparison_cases(rng)
    OUT.write_text(json.dumps({"cases": cases}, ensure_ascii=False, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
