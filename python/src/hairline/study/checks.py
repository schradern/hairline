"""Checks a study runs when it is created; they report, they never change the data."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from hairline.numbers import format_number, format_percent
from hairline.study.columns import NUMBER, is_missing, is_text, level_text, row_numbers
from hairline.tokens import load_tokens


@dataclass(frozen=True)
class Finding:
    """One problem: `level` is "error" (the endpoint cannot run) or "warning" (the result is still computed)."""

    level: str
    column: str
    problem: str
    rows: tuple[int, ...]
    fix: str

    def __str__(self) -> str:
        rows = f" (rows {', '.join(map(str, self.rows))})" if self.rows else ""
        return f"{self.level}: {self.column}: {self.problem}{rows}. Fix: {self.fix}."


def count_text(count: int) -> str:
    return format_number(count, 0)


def missing_values(data: pd.DataFrame, column: str, limit: int) -> list[Finding]:
    mask = is_missing(data[column])
    if not mask.any():
        return []
    problem = f"{count_text(int(mask.sum()))} missing ({format_percent(mask.mean(), 1)})"
    return [Finding("warning", column, problem, tuple(row_numbers(mask, limit)),
                    "endpoints leave these rows out for this column")]


def spellings(data: pd.DataFrame, column: str, limit: int) -> list[Finding]:
    """Values that differ only in case or surrounding spaces."""
    series = data[column]
    if not is_text(series):
        return []
    values = series[~is_missing(series)].map(level_text)
    variants: dict[str, list[str]] = {}
    for value in values:
        spelled = variants.setdefault(value.strip().lower(), [])
        if value not in spelled:
            spelled.append(value)
    clashes = [spelled for spelled in variants.values() if len(spelled) > 1]
    if not clashes:
        return []
    listed = "; ".join(" / ".join(f"'{value}'" for value in spelled) for spelled in clashes)
    first = {key: spelled[0] for key, spelled in variants.items()}
    texts = series.map(level_text)
    mask = ~is_missing(series) & texts.map(lambda value: value != first.get(value.strip().lower(), value))
    return [Finding("warning", column, f"spellings that differ only in case or spaces: {listed}",
                    tuple(row_numbers(mask.astype(bool), limit)), "recode to one spelling before the study")]


def numbers_as_text(data: pd.DataFrame, column: str) -> list[Finding]:
    series, share = data[column], load_tokens()["study"]["numeric_text_share"]
    values = series[~is_missing(series)].map(str)
    if not is_text(series) or values.empty:
        return []
    numeric = values.map(lambda value: bool(NUMBER.match(value))).mean()
    if numeric < share:
        return []
    return [Finding("warning", column, f"stored as text, but {format_percent(numeric, 0)} of the values are numbers",
                    (), "convert the column to numbers, or declare it categorical")]
