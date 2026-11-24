"""Columns beside spread rows: other measures of each group, written in the numbers column, not drawn."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

from hairline.charts.common import check_columns, check_numeric, humanise
from hairline.charts.summaries import DASH, measure_numbers, stat_label, stat_text, summary_values
from hairline.numbers import listed

CENTRES = ("median", "mean")
INTERVALS = ("iqr", "sd", "ci", "range")


def checked_columns(data: pd.DataFrame, columns: str | Sequence[str] | Mapping[str, str] | None,
                    chart: str) -> dict[str, str]:
    """The columns to write, each with its label: one name, several, or {column: label}; numbers only."""
    if columns is None:
        return {}
    if isinstance(columns, str):
        named = {columns: humanise(columns)}
    elif isinstance(columns, Mapping):
        named = {str(column): str(label) for column, label in columns.items()}
    else:
        named = {str(column): humanise(column) for column in columns}
    check_columns(data, list(named))
    check_numeric(data, list(named), chart)
    return named


def column_measures(stats: Sequence[str]) -> tuple[str, str | None]:
    """What each written column shows, taken from the chart's own `stats`: its first centre (median unless the
    mean is asked for) and its first interval, if any ("mean", "iqr" gives "4.7 (3.5–6.8)")."""
    centre = next((name for name in stats if name in CENTRES), "median")
    return centre, next((name for name in stats if name in INTERVALS), None)


def column_numbers(data: pd.DataFrame, columns: Mapping[str, str]) -> dict:
    """Each column's formatters, from all its values, so every row of a column has the same decimals."""
    return {column: measure_numbers(data[column].dropna().astype(float).to_numpy(), False, None)
            for column in columns}


def column_pairs(rows: pd.DataFrame, columns: Mapping[str, str], measures: tuple[str, str | None],
                 numbers: dict) -> list[list[str]]:
    """A (label, value) pair per column for one group: 'Age', '61.4 (53–73)'; a dash without values."""
    centre, interval = measures
    pairs = []
    for column, label in columns.items():
        values = rows[column].dropna().astype(float).to_numpy()
        if not len(values):
            pairs.append([label, DASH])
            continue
        found = summary_values(values, False)
        text = stat_text(centre, found, numbers[column], values)
        if interval is not None:
            text += f" ({stat_text(interval, found, numbers[column], values)})"
        pairs.append([label, text])
    return pairs


def columns_note(columns: Mapping[str, str], measures: tuple[str, str | None], locale: str) -> str | None:
    """The caption's account of the written columns: 'Age and length of stay: Median (IQR).'"""
    if not columns:
        return None
    centre, interval = measures
    shown = stat_label(centre, locale) + (f" ({stat_label(interval, locale)})" if interval else "")
    return f"{listed(list(columns.values()))}: {shown}."


def group_columns(frames: Mapping[str, pd.DataFrame], name: str, columns: Mapping[str, str],
                  measures: tuple[str, str | None], numbers: dict) -> list[list[str]]:
    """The written columns of group `name`, or none when the chart has none."""
    return column_pairs(frames[name], columns, measures, numbers) if columns else []



def with_columns(pairs: list[list[str]], stats: int, columns: list[list[str]]) -> list[list[str]]:
    """The written columns right after the `stats` key numbers, before a mark: every row then has them at the same
    positions, under their headings, whether or not it has a mark."""
    return pairs[:stats] + columns + pairs[stats:]
