"""Reading study columns the same way in both languages: missing values, numbers stored as text, level names."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

NUMBER = re.compile(r"^\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?\s*$")


def is_missing(series: pd.Series) -> pd.Series:
    """Missing: NA/NaN/None, or text that is empty after stripping spaces."""
    blank = series.map(lambda value: isinstance(value, str) and not value.strip())
    return series.isna() | blank.astype(bool)


def level_text(value: object) -> str:
    """A category as text: whole floats without '.0', booleans as Yes/No (as in R)."""
    if isinstance(value, (bool, np.bool_)):
        return "Yes" if value else "No"
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))
    return str(value)


def levels(series: pd.Series, ordered: bool = True) -> list[str]:
    """Non-missing categories: a categorical column's own order; otherwise sorted (as numbers when all are
    numbers, else by code point, as R's radix sort); with `ordered=False`, order of first appearance."""
    present = list(dict.fromkeys(level_text(value) for value in series[~is_missing(series)]))
    if isinstance(series.dtype, pd.CategoricalDtype):
        return [name for name in map(level_text, series.cat.categories) if name in present]
    if not ordered:
        return present
    if all(NUMBER.match(name) for name in present):
        return sorted(present, key=float)
    return sorted(present)


def is_text(series: pd.Series) -> bool:
    return not pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)


def infer_type(series: pd.Series) -> str:
    """Numeric when stored as numbers with more than two distinct values; otherwise categorical."""
    if is_text(series) or pd.api.types.is_bool_dtype(series):
        return "categorical"
    return "numeric" if series[~is_missing(series)].nunique() > 2 else "categorical"


def numbers(series: pd.Series) -> np.ndarray:
    """Non-missing values as floats."""
    return series[~is_missing(series)].astype(float).to_numpy()


def row_numbers(mask: pd.Series, limit: int) -> list[int]:
    """1-based positions of the first `limit` rows where `mask` holds."""
    return [int(position) + 1 for position in np.flatnonzero(mask.to_numpy())[:limit]]
