"""Marginal bars of a heatmap: each column's mean (or sum) of `z` as a bar above it, each row's as a bar to its right,
in grey so the ramp keeps the colour, the largest of each written at its end. The bars add room to the figure
rather than take it from the cells. The values come from the grid, the geometry
in pt from the cells' rectangle. Pure; mirrored in R's heatmap_margins.R."""

from __future__ import annotations

import numpy as np

from hairline.charts.donut_geometry import Measure, text
from hairline.charts.grid_values import value_texts
from hairline.charts.tips import tagged
from hairline.layout.geometry import Box
from hairline.numbers import word
from hairline.tokens import load_tokens

KINDS = {"mean": "mean", "sum": "sum"}


def check_margins(margins: str | None, chart: str) -> None:
    if margins is not None and margins not in KINDS:
        raise ValueError(f"hairline: {chart}: margins {margins!r} must be 'mean', 'sum' or None")


def aggregated(values: np.ndarray, kind: str) -> float | None:
    """The mean or sum of the known values; None when none is known."""
    known = values[np.isfinite(values)]
    if not len(known):
        return None
    return float(known.mean() if kind == "mean" else known.sum())


def margin_spec(grid: np.ndarray, kind: str, percent: bool, locale: str, chart: str) -> dict:
    """Each column's and each row's mean or sum, written as the cells' values are."""
    columns = [aggregated(grid[:, column], kind) for column in range(grid.shape[1])]
    rows = [aggregated(grid[row, :], kind) for row in range(grid.shape[0])]
    known = [value for value in columns + rows if value is not None]
    if min(known) < 0:
        raise ValueError(f"hairline: {chart}: margins draw bars from zero, so they need a {kind} of zero or more in "
                         f"every row and column; the lowest is {min(known):g}")
    texts = iter(value_texts(known, percent, locale))
    written = [[next(texts) if value is not None else "" for value in values] for values in (columns, rows)]
    return {"columns": columns, "rows": rows, "texts": {"columns": written[0], "rows": written[1]},
            "word": word(KINDS[kind], locale)}


def peak(values: list[float | None]) -> int:
    """The first of the largest values."""
    return max(range(len(values)), key=lambda index: (values[index] or 0.0, -index))


def margin_scene(margins: dict | None, measure: Measure, style: dict) -> dict | None:
    """The bars' values with their colour, the band, gaps and the widest peak label in pt."""
    if margins is None:
        return None
    rules, base = load_tokens()["heatmap"], style["base"]
    label = measure(margins["texts"]["rows"][peak(margins["rows"])], "label")
    return {**margins, "color": style["neutral"]["axis"], "band": rules["margin_band"] * base,
            "gap": rules["margin_gap"] * base, "pad": rules["margin_pad"] * base, "bar_gap": rules["margin_bar_gap"],
            "label_width": label}


def margin_reserve(scene: dict | None, line: float) -> tuple[float, float]:
    """The room the bars take above the cells and to their right."""
    if scene is None:
        return 0.0, 0.0
    return line + scene["pad"] + scene["band"] + scene["gap"], \
        scene["gap"] + scene["band"] + scene["pad"] + scene["label_width"]


def bar(left: float, top: float, right: float, bottom: float, color: str) -> dict:
    return {"kind": "polygon", "points": [[left, top], [right, top], [right, bottom], [left, bottom]], "fill": color,
            "part": "margin"}


def column_bars(scene: dict, margins: dict, plot: Box, glyphs: dict) -> list[dict]:
    """A bar above each column with a value, rising from the band's foot, the largest written above it."""
    xs, values, largest = scene["x_edges"], margins["columns"], peak(margins["columns"])
    foot, top = plot.y - margins["gap"], max(margins["columns"][largest], 0.0)
    shapes = []
    for column, value in enumerate(values):
        if value is None:
            continue
        inset = (xs[column + 1] - xs[column]) * plot.width * margins["bar_gap"] / 2
        left, right = plot.x + xs[column] * plot.width + inset, plot.x + xs[column + 1] * plot.width - inset
        height = margins["band"] * value / top if top > 0 else 0.0
        where = " ".join(part for part in (scene["titles"]["x"], scene["tips"]["x"][column]) if part)
        shapes.append(tagged(bar(left, foot - height, right, foot, margins["color"]), where,
                             f"{where}: {margins['word']} {margins['texts']['columns'][column]}"))
        if column == largest:
            shapes.append({**text((left + right) / 2, foot - height - margins["pad"] - glyphs["descender"],
                                  margins["texts"]["columns"][column], "label", glyphs["ticks"], "center"),
                           "part": "margin"})
    return shapes


def row_bars(scene: dict, margins: dict, plot: Box, glyphs: dict) -> list[dict]:
    """A bar to the right of each row with a value, from the band's start, the largest written after it. A bar
    belongs to its row's series, so it lights up with the row's cells."""
    ys, values, largest = scene["y_edges"], margins["rows"], peak(margins["rows"])
    start, top = plot.x + plot.width + margins["gap"], max(margins["rows"][largest], 0.0)
    shapes = []
    for row, value in enumerate(values):
        if value is None:
            continue
        inset = (ys[row + 1] - ys[row]) * plot.height * margins["bar_gap"] / 2
        upper, lower = plot.y + (1 - ys[row + 1]) * plot.height + inset, plot.y + (1 - ys[row]) * plot.height - inset
        length = margins["band"] * value / top if top > 0 else 0.0
        where = " ".join(part for part in (scene["titles"]["y"], scene["tips"]["y"][row]) if part)
        shapes.append(tagged(bar(start, upper, start + length, lower, margins["color"]), where,
                             f"{where}: {margins['word']} {margins['texts']['rows'][row]}"))
        if row == largest:
            shapes.append({**text(start + length + margins["pad"], (upper + lower) / 2 + glyphs["cap"] / 2,
                                  margins["texts"]["rows"][row], "label", glyphs["ticks"]), "part": "margin"})
    return shapes


def margin_shapes(scene: dict, plot: Box) -> list[dict]:
    """The bars above the columns and right of the rows, with their peak labels; none without margins."""
    margins = scene.get("margins")
    if margins is None:
        return []
    return column_bars(scene, margins, plot, scene["text"]) + row_bars(scene, margins, plot, scene["text"])
