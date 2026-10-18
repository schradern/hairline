"""Role-specific checks: follow-up time, events, groups and ids."""

from __future__ import annotations

import numpy as np
import pandas as pd

from hairline.study.checks import Finding, count_text, missing_values, spellings
from hairline.study.columns import is_missing, level_text, row_numbers
from hairline.tokens import load_tokens


def time_findings(data: pd.DataFrame, column: str, limit: int) -> list[Finding]:
    values = pd.to_numeric(data[column].where(~is_missing(data[column])), errors="coerce")
    bad = values.isna() | (values < 0)
    if not bad.any():
        return []
    return [Finding("error", column, f"{count_text(int(bad.sum()))} follow-up times are missing, negative or not "
                    "numbers", tuple(row_numbers(bad, limit)),
                    "correct or drop these rows; times count from the start of follow-up")]


def is_event_value(value: object) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return True
    if isinstance(value, str) or pd.isna(value):
        return False
    return value in (0, 1)


def event_findings(data: pd.DataFrame, column: str, limit: int) -> list[Finding]:
    bad = ~data[column].map(is_event_value).astype(bool)
    if not bad.any():
        return []
    return [Finding("error", column, f"{count_text(int(bad.sum()))} event values are not 0/1 (or TRUE/FALSE)",
                    tuple(row_numbers(bad, limit)), "code events as 1 (event) and 0 (censored)")]


def group_findings(data: pd.DataFrame, column: str, groups: list[str], limit: int) -> list[Finding]:
    findings = missing_values(data, column, limit) + spellings(data, column, limit)
    labels = data[column].map(lambda value: None if pd.isna(value) else level_text(value))
    for name in groups:
        size = int((labels == name).sum())
        if size < load_tokens()["study"]["small_group"]:
            findings.append(Finding("warning", column, f"group '{name}' has {count_text(size)} rows", (),
                                    "merge it with a similar group or leave it out of comparisons"))
    return findings


def id_findings(data: pd.DataFrame, column: str, limit: int) -> list[Finding]:
    present = data[column][~is_missing(data[column])].map(level_text)
    repeated = present.duplicated()
    if not repeated.any():
        return []
    mask = pd.Series(False, index=data.index)
    mask[present.index[repeated.to_numpy()]] = True
    return [Finding("warning", column, f"{count_text(int(repeated.sum()))} rows repeat an id",
                    tuple(row_numbers(mask, limit)),
                    "keep one row per id, or leave out the id role if rows are visits")]
