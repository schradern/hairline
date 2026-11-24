"""profile(): one cohort at a glance, each variable in a tile of its own beside its Table 1 rows; with `by`, every
tile is split into the same coloured groups."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import pandas as pd

from hairline.charts.timeseries import iso_datetimes
from hairline.numbers import format_number
from hairline.study.columns import is_missing, is_text
from hairline.study.describe import categorical_rows, numeric_rows
from hairline.study.profile_strata import MISSING, Stratum, strata
from hairline.study.profile_tiles import profile_figure
from hairline.study.result import Result, figure_for
from hairline.study.summaries import EMPTY, counted_text, listed

if TYPE_CHECKING:
    from hairline.study.model import Study


def date_values(study: Study, name: str) -> pd.Series:
    """The column's dates without missing values; ISO date text is read as dates, anything else is refused."""
    if name not in study.data.columns:
        raise ValueError(f"hairline: profile: date column '{name}' is not in the data; columns: "
                         f"{', '.join(map(str, study.data.columns))}")
    column = study.data[name]
    present = column[~is_missing(column)]
    if pd.api.types.is_datetime64_any_dtype(present):
        return present
    parsed = iso_datetimes(present) if is_text(present) else pd.Series(pd.NaT, index=present.index)
    if parsed.isna().any():
        bad = present[parsed.isna()].iloc[0]
        raise ValueError(f"hairline: profile: '{name}' has {bad!r}, which is not a date or ISO date text "
                         "(2025-01-31)")
    return parsed


def date_rows(study: Study, name: str, dates: pd.Series, parts: list) -> tuple[list[list[str]], dict, dict]:
    """'Surgery date, first to last' and '2022-01-05 to 2024-12-28' per column (a dash without dates)."""
    found, spans = {}, []
    for label, rows in parts:
        days = dates[dates.index.isin(rows.index)]
        spans.append(f"{days.min():%Y-%m-%d} to {days.max():%Y-%m-%d}" if len(days) else EMPTY)
        found[label] = {"n": len(days), "missing": len(rows) - len(days),
                        "first": days.min() if len(days) else pd.NaT, "last": days.max() if len(days) else pd.NaT}
    values = {name: {label: span for (label, _), span in zip(parts, spans, strict=True)}}
    return [[f"{study.label(name)}, first to last", *spans]], values, found


def missing_sentence(study: Study, found: dict) -> str:
    """' Missing: Weight 12.'; empty when every value is there."""
    missing = {name: entry[study.overall]["missing"] for name, entry in found.items()}
    parts = [f"{study.label(name)} {format_number(count, 0)}" for name, count in missing.items() if count]
    return f" Missing: {listed(parts)}." if parts else ""


def counts_sentence(study: Study, groups: list[Stratum], by: str | None) -> str:
    """'412 patients.', or by group: '412 patients; by sex, 181 Female and 231 Male. 3 without a sex are in
    Overall only.'"""
    total = counted_text(len(study.data), study.nouns)
    if by is None:
        return f"{total}."
    named = [stratum for stratum in groups if stratum.name != MISSING]
    counts = listed([f"{format_number(int(stratum.mask.sum()), 0)} {stratum.name}" for stratum in named])
    rest = sum(int(stratum.mask.sum()) for stratum in groups if stratum.name == MISSING)
    left = f" {format_number(rest, 0)} without a {study.in_sentence(by)} are in Overall only." if rest else ""
    return f"{total}; by {study.in_sentence(by)}, {counts}.{left}"


def table_parts(study: Study, groups: list[Stratum], by: str | None) -> list[tuple[str, pd.DataFrame]]:
    """A column per group of `by`, then Overall (every row); without `by` only Overall."""
    named = [(stratum.name, study.data[stratum.mask]) for stratum in groups if by and stratum.name != MISSING]
    return [*named, (study.overall, study.data)]


def profile(study: Study, dates: str | Sequence[str] = (), by: str | None = None, size: str = "double") -> Result:
    """The whole cohort: a histogram per numeric variable, shares per category and, for each of `dates`, rows per
    month (quarter, year). `by` names a column of a few groups (sex, arm) that splits every tile in the session's
    colours; the table then has a column per group before Overall."""
    dates = (dates,) if isinstance(dates, str) else tuple(dates)
    study.require(list(study.variables), "profile")
    study.require_one_row("profile")
    parsed = {name: date_values(study, name) for name in dict.fromkeys(dates)}
    groups = strata(study, by)
    parts = table_parts(study, groups, by)
    counts = [format_number(len(rows), 0) for _, rows in parts]
    table, values, found = [["n", *counts]], {"n": {label: count for (label, _), count in zip(parts, counts,
                                                                                                strict=True)}}, {}
    for name in study.variables:
        rows, shown, found[name] = (numeric_rows(study, name, parts, ("median_iqr",))
                                    if study.types[name] == "numeric" else categorical_rows(study, name, parts))
        table += rows
        values.update(shown)
    for name, column in parsed.items():
        rows, shown, found[name] = date_rows(study, name, column, parts)
        table += rows
        values.update(shown)
    text = counts_sentence(study, groups, by) + missing_sentence(study, found)
    frame = pd.DataFrame(table, columns=["Characteristic", *[label for label, _ in parts]])
    named = [stratum.name for stratum in groups if stratum.name not in (None, MISSING)]
    figure = figure_for("profile", named, "groups", lambda: profile_figure(study, parsed, groups, by, size))
    return Result(figure, frame, values, text, {"n": len(study.data), "variables": found})
