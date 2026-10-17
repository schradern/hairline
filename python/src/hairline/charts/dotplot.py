"""Dot plot with intervals: sorted by value, labels on the left, the value on the right."""

from __future__ import annotations

import pandas as pd

from hairline.charts.common import check_columns, humanise
from hairline.charts.forest import forest_spec
from hairline.charts.forest_geometry import forest_drawing
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.settings import current_settings


def dotplot(data: pd.DataFrame, label: str, estimate: str, low: str | None = None, high: str | None = None, *,
            title: str | None = None, subtitle: str | None = None, caption: str | None = None, sort: bool = True,
            ratio: bool = False, reference: float | None = None, digits: int = 2,
            size: str = "onehalf") -> HairlineFigure:
    """One dot per row, largest at the top; with `low` and `high` an interval and its numbers on the right.
    `reference` draws a vertical line (a target or a null value)."""
    check_columns(data, [label, estimate, low, high])
    interval = low is not None and high is not None
    rows = data.sort_values(estimate, ascending=False, kind="mergesort") if sort else data
    if not interval:
        rows = rows.assign(_low=rows[estimate], _high=rows[estimate])
        low, high = "_low", "_high"
    heading = f"{humanise(estimate)} [95 % CI]" if interval else humanise(estimate)
    spec = forest_spec(rows, label, estimate, low, high, ratio=ratio, color=current_settings().palette[0],
                       study_heading=humanise(label), effect_heading=heading, digits=digits, marker="dot",
                       interval=interval, null=reference)
    result = figure(title or f"{humanise(estimate)} by {str(label).replace('_', ' ')}", subtitle=subtitle,
                    caption=caption, size=size)
    result.draw(0, lambda box, measure, style: forest_drawing(spec, box, measure, style))
    return fit_height(result)
