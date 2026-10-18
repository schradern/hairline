"""Formatted summaries for study tables and values: digits by magnitude, median (IQR), mean (SD), n (%)."""

from __future__ import annotations

import numpy as np

from hairline.numbers import format_number, format_percent
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
    """Decimals by the median magnitude: none from 10, one from 1, two below (tokens study.digit_steps)."""
    magnitude = float(np.median(np.abs(values))) if len(values) else 0.0
    for step in load_tokens()["study"]["digit_steps"]:
        if magnitude >= step["min"]:
            return step["digits"]
    return load_tokens()["study"]["digit_steps"][-1]["digits"]


def numeric_text(values: np.ndarray, stat: str, digits: int, missing: int) -> str:
    if stat == "n_missing":
        return format_number(missing, 0)
    if not len(values):
        return EMPTY

    def number(value: float) -> str:
        # Snap away float noise first: R and numpy reach the same quantile by different arithmetic.
        return format_number(round(value, SNAP_DIGITS), digits)
    if stat == "median_iqr":
        low, middle, high = quantiles(values, [0.25, 0.5, 0.75])
        return f"{number(middle)} ({number(low)}{EMPTY}{number(high)})"
    if stat == "mean_sd":
        spread = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
        return f"{number(float(np.mean(values)))} ({number(spread)})"
    return f"{number(float(np.min(values)))}{EMPTY}{number(float(np.max(values)))}"


def count_share(count: int, total: int) -> str:
    """'42 (23.3%)'; the share of the non-missing values in that column."""
    share = format_percent(count / total, load_tokens()["study"]["percent_digits"]) if total else EMPTY
    return f"{format_number(count, 0)} ({share})"
