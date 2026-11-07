"""Dot plot with intervals: sorted by value, labels on the left, the value on the right."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from hairline.charts.common import (
    check_columns,
    check_numeric,
    drop_small,
    humanise,
    labels_with_n,
    ordered_names,
    with_caption,
)
from hairline.charts.forest import forest_spec
from hairline.charts.forest_geometry import forest_drawing
from hairline.charts.options import Reference, checked_highlight, references
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.marks import context_color, lone_color
from hairline.numbers import word
from hairline.settings import current_settings


def dotplot(data: pd.DataFrame, label: str, estimate: str, low: str | None = None, high: str | None = None, *,
            title: str | None = None, subtitle: str | None = None, caption: str | None = None, sort: bool = True,
            ratio: bool = False, reference: Reference = None, digits: int | None = None,
            size: str = "onehalf", n: str | None = None, percent: bool = False, order: Sequence[str] | None = None,
            min_n: int | None = None, x_title: str | None = None,
            highlight: Sequence[str] | str | None = None) -> HairlineFigure:
    """One dot per row, largest at the top; with `low` and `high` an interval and its numbers on the right.
    `n` names the column holding each row's n, written after its label in the locale ("Medical (n = 1,010)").
    `percent=True` draws shares (0.15) as percent (15), the heading naming the unit. `order` gives the rows'
    order instead of sorting by value.

    Shared with the other charts: `reference` draws dashed lines (a target, a null value: 0.1, (0.1, "Target") or
    {"Target": 0.1}); `min_n` leaves out rows whose `n` is smaller and names them; `x_title` titles the axis;
    `highlight` keeps these rows in colour."""
    check_columns(data, [label, estimate, low, high, n])
    if (low is None) != (high is None):
        raise ValueError(f"hairline: dotplot: an interval needs both low and high; got only "
                         f"{'low' if low is not None else 'high'}={low if low is not None else high!r}")
    interval = low is not None and high is not None
    data = as_percent(data, [estimate, low, high]) if percent else data
    data, small = rows_with_min_n(data, label, n, min_n)
    rows = ordered_rows(data, label, estimate, sort, order)
    names = [str(name) for name in rows[label]]
    chosen = checked_highlight(highlight, names, "dotplot")
    if n is not None:
        check_numeric(rows, [n], "dotplot")
        rows = rows.assign(**{label: labels_with_n(names, dict(zip(names, rows[n], strict=True)),
                                                    current_settings().locale)})
    if not interval:
        rows = rows.assign(_low=rows[estimate], _high=rows[estimate])
        low, high = "_low", "_high"
    name = f"{humanise(estimate)} (%)" if percent else humanise(estimate)
    heading = word("interval", name=name) if interval else name
    spec = forest_spec(rows, label, estimate, low, high, ratio=ratio, color=lone_color(),
                       study_heading=humanise(label), effect_heading=heading, digits=digits, marker="dot",
                       interval=interval, null=None, references=references(reference, "dotplot"), axis_title=x_title)
    if chosen:
        grey = context_color(current_settings())
        for row, row_name in zip(spec["rows"], names, strict=True):
            row["color"] = spec["color"] if row_name in chosen else grey
    result = figure(title or f"{humanise(estimate)} by {str(label).replace('_', ' ')}", subtitle=subtitle,
                    caption=with_caption(caption, small), size=size)
    result.draw(0, lambda box, measure, style: forest_drawing(spec, box, measure, style))
    return fit_height(result)


def rows_with_min_n(data: pd.DataFrame, label: str, n: str | None, min_n: int | None) -> tuple[pd.DataFrame,
                                                                                                str | None]:
    """Rows whose `n` reaches `min_n`, and the caption note naming the others; `min_n` needs the n column."""
    if min_n is None:
        return data, None
    if n is None:
        raise ValueError("hairline: dotplot: min_n needs n=, the column holding each row's n")
    check_numeric(data, [n], "dotplot")
    kept, note = drop_small([(str(name), np.ones(int(count))) for name, count in zip(data[label], data[n],
                                                                                       strict=True)],
                            min_n, "dotplot")
    return data[data[label].astype(str).isin(dict(kept))], note


def ordered_rows(data: pd.DataFrame, label: str, estimate: str, sort: bool, order: Sequence[str] | None) -> \
        pd.DataFrame:
    """The rows in `order` when given, else largest first when sorted, else as given."""
    if order is not None:
        names = ordered_names(data[label], order, "dotplot", label)
        return data.set_index(data[label].astype(str)).loc[names].reset_index(drop=True)
    return data.sort_values(estimate, ascending=False, kind="mergesort") if sort else data


def as_percent(data: pd.DataFrame, columns: list[str | None]) -> pd.DataFrame:
    """Shares as percent: each named column × 100."""
    check_numeric(data, [column for column in columns if column], "dotplot")
    return data.assign(**{column: data[column] * 100 for column in columns if column})
