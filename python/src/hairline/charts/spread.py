"""Spread rows: per group the range as a thin line, the interquartile range as a band in the group's colour, the
median as a dot, an optional reference tick, and the key numbers in a column on the right."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from hairline import entities
from hairline.charts.common import check_columns, check_numeric, humanise
from hairline.charts.forest import decimals
from hairline.charts.spread_geometry import spread_drawing
from hairline.charts.timeseries import groups_of
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.numbers import auto_digits, format_number, is_whole, locale_symbols, quantile_places
from hairline.stats.density import quantiles
from hairline.ticks import axis_limits, nice_breaks

STATS = ("median", "iqr", "mean", "n", "range")
SNAP_DIGITS = 10
DASH = "–"


def number_formatter(values: np.ndarray, percent: bool, digits: int | None, extra: int = 0):
    """Formats values with digits by magnitude (of the percentage for shares), plus `extra` decimals (one for
    means of whole numbers); float noise snapped first."""
    scale = 100.0 if percent else 1.0
    places = (digits if digits is not None else auto_digits(values * scale)) + extra
    suffix = locale_symbols(None)["percent_space"] + "%" if percent else ""
    return lambda value: format_number(round(float(value) * scale, SNAP_DIGITS), places) + suffix


def stats_pairs(values: np.ndarray, stats: Sequence[str], numbers: tuple, mark: float | None,
                mark_label: str | None) -> list[list[str]]:
    """Key numbers as (label, value) pairs, drawn like a panel header's key numbers."""
    number, mean_number = numbers
    low, q1, middle, q3, high = quantiles(values, [0, 0.25, 0.5, 0.75, 1])
    parts = {"median": ["Median", number(middle)], "iqr": ["IQR", f"{number(q1)}{DASH}{number(q3)}"],
             "mean": ["Mean", mean_number(np.mean(values))], "n": ["n", format_number(len(values), 0)],
             "range": ["Range", f"{number(low)}{DASH}{number(high)}"]}
    pairs = [parts[name] for name in stats]
    if mark is not None and mark_label:
        pairs.append([mark_label, number(mark)])
    return pairs


def spread_axis(lows: list[float], highs: list[float], percent: bool, zero: bool) -> dict:
    low, high = min(lows + ([0.0] if zero else [])), max(highs + ([0.0] if zero else []))
    breaks = nice_breaks(low, high)
    limits = axis_limits(low, high, breaks)
    shown = [value * (100 if percent else 1) for value in breaks]
    places = decimals([round(value, SNAP_DIGITS) for value in shown])
    labels = [format_number(round(value, SNAP_DIGITS), places) for value in shown]
    if percent:
        labels[-1] += locale_symbols(None)["percent_space"] + "%"
    return {"breaks": breaks, "labels": labels, "low": limits[0], "high": limits[1]}


def spread_spec(data: pd.DataFrame, group: str, value: str, *, order: Sequence[str] | None = None,
                marks: Mapping[str, float] | None = None, mark_label: str | None = None,
                stats: Sequence[str] = ("median", "iqr", "mean"), percent: bool = False, digits: int | None = None,
                zero: bool = False, axis_title: str | None = None, colors: Mapping[str, str] | None = None) -> dict:
    check_columns(data, [group, value])
    check_numeric(data, [value], "spread")
    unknown = [name for name in stats if name not in STATS]
    if unknown:
        raise ValueError(f"hairline: spread: unknown statistic {unknown[0]!r}; use any of {', '.join(STATS)}")
    groups = [(str(name), rows[value].dropna().astype(float).to_numpy())
              for name, rows in groups_of(data, group, order, "spread")]
    groups = [(name, values) for name, values in groups if len(values)]
    if not groups:
        raise ValueError(f"hairline: spread: no values to draw; '{value}' is empty or missing in every row")
    every = np.concatenate([values for _, values in groups])
    whole = is_whole(every) and not percent
    plain, mean_number = number_formatter(every, percent, digits), number_formatter(every, percent, digits,
                                                                                    1 if whole else 0)
    whole = whole and digits is None
    # Of whole numbers, a quantile between two of them keeps one decimal (a median of 2.5, not 3).
    numbers = ((lambda value: mean_number(value) if quantile_places(value, 0, whole) else plain(value)), mean_number)
    palette, marks = entities.colors_for([name for name, _ in groups], colors), dict(marks or {})
    rows = []
    for name, values in groups:
        low, q1, middle, q3, high = quantiles(values, [0, 0.25, 0.5, 0.75, 1])
        mark = marks.get(name)
        rows.append({"name": name, "color": palette[name], "low": low, "q1": q1, "median": middle, "q3": q3,
                     "high": high, "mark": None if mark is None else float(mark),
                     "pairs": stats_pairs(values, stats, numbers, mark, mark_label)})
    lows = [row["low"] for row in rows] + [row["mark"] for row in rows if row["mark"] is not None]
    highs = [row["high"] for row in rows] + [row["mark"] for row in rows if row["mark"] is not None]
    return {"rows": rows, "axis": spread_axis(lows, highs, percent, zero), "axis_title": axis_title}


def spread(data: pd.DataFrame, group: str, value: str, *, title: str | None = None, subtitle: str | None = None,
           caption: str | None = None, order: Sequence[str] | None = None, marks: Mapping[str, float] | None = None,
           mark_label: str | None = None, stats: Sequence[str] = ("median", "iqr", "mean"), percent: bool = False,
           digits: int | None = None, zero: bool = False, axis_title: str | None = None,
           colors: Mapping[str, str] | None = None, size: str = "onehalf") -> HairlineFigure:
    """Distributions per group compared on one axis, first group on top; `marks` adds a reference tick per group
    (a capacity, a target), `mark_label` names it in the numbers column; `axis_title` (e.g. the unit) goes under
    the axis numbers."""
    spec = spread_spec(data, group, value, order=order, marks=marks, mark_label=mark_label, stats=stats,
                       percent=percent, digits=digits, zero=zero, axis_title=axis_title, colors=colors)
    result = figure(title or f"{humanise(value)} by {str(group).replace('_', ' ')}", subtitle=subtitle,
                    caption=caption, size=size)
    result.draw(0, lambda box, measure, style: spread_drawing(spec, box, measure, style))
    return fit_height(result)
