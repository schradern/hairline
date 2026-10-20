"""Formatted summaries for study tables and values: digits by magnitude, median (IQR), mean (SD), n (%)."""

from __future__ import annotations

import numpy as np

from hairline.numbers import auto_digits, format_number, format_percent, quantile_places
from hairline.stats.density import quantiles
from hairline.tokens import load_tokens

STAT_LABELS = {"median_iqr": "median (IQR)", "mean_sd": "mean (SD)", "range": "range", "n_missing": "missing"}
EMPTY = "–"
SNAP_DIGITS = 10


def check_stats(stats: tuple[str, ...]) -> None:
    for name in stats:
        if name not in STAT_LABELS:
            raise ValueError(f"hairline: study: unknown statistic {name!r}; use one of {', '.join(STAT_LABELS)}")


def digits_for(values: np.ndarray) -> int:
    return auto_digits(values)


def mean_text(values: np.ndarray, digits: int, whole: bool) -> str:
    """The mean, with one more decimal when the variable holds whole numbers."""
    if not len(values):
        return EMPTY
    return format_number(round(float(np.mean(values)), SNAP_DIGITS), digits + (1 if whole else 0))


def numeric_text(values: np.ndarray, stat: str, digits: int, missing: int, whole: bool = False) -> str:
    """One statistic as text; `whole` (the variable holds whole numbers) gives means one more decimal."""
    if stat == "n_missing":
        return format_number(missing, 0)
    if not len(values):
        return EMPTY

    def number(value: float) -> str:
        # Snap away float noise first: R and numpy reach the same quantile by different arithmetic.
        return format_number(round(value, SNAP_DIGITS), quantile_places(value, digits, whole))
    if stat == "median_iqr":
        low, middle, high = quantiles(values, [0.25, 0.5, 0.75])
        return f"{number(middle)} ({number(low)}{EMPTY}{number(high)})"
    if stat == "mean_sd":
        spread = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
        places = digits + (1 if whole else 0)
        return f"{mean_text(values, digits, whole)} ({format_number(round(spread, SNAP_DIGITS), places)})"
    return f"{number(float(np.min(values)))}{EMPTY}{number(float(np.max(values)))}"


def count_share(count: int, total: int) -> str:
    """'42 (23.3%)'; the share of the non-missing values in that column."""
    share = format_percent(count / total, load_tokens()["study"]["percent_digits"]) if total else EMPTY
    return f"{format_number(count, 0)} ({share})"
