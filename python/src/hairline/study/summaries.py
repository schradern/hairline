"""Formatted summaries for study tables and values: digits by magnitude, median (IQR), mean (SD), n (%)."""

from __future__ import annotations

import math

import numpy as np

from hairline.numbers import auto_digits, format_number, format_percent, quantile_places
from hairline.stats.density import quantiles
from hairline.tokens import load_tokens

STAT_LABELS = {"median_iqr": "median (IQR)", "mean_sd": "mean (SD)", "range": "range", "n_missing": "missing"}
EMPTY = "–"
SNAP_DIGITS = 10
STAT_KEYS = {"median_iqr": ("median", "q1", "q3"), "mean_sd": ("mean", "sd"), "range": ("min", "max"),
             "n_missing": ()}


def check_stats(stats: tuple[str, ...]) -> None:
    for name in stats:
        if name not in STAT_LABELS:
            raise ValueError(f"hairline: study: unknown statistic {name!r}; use one of {', '.join(STAT_LABELS)}")


def digits_for(values: np.ndarray) -> int:
    return auto_digits(values)


def summary_numbers(values: np.ndarray, stats: tuple[str, ...], missing: int) -> dict:
    """The unrounded quantities behind the statistics: n and missing, then each statistic's own (NaN without
    values)."""
    found: dict = {"n": len(values), "missing": missing}
    for stat in stats:
        found.update(dict.fromkeys(STAT_KEYS[stat], math.nan))
        if not len(values):
            continue
        if stat == "median_iqr":
            found["q1"], found["median"], found["q3"] = quantiles(values, [0.25, 0.5, 0.75])
        elif stat == "mean_sd":
            found["mean"] = float(np.mean(values))
            found["sd"] = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
        elif stat == "range":
            found["min"], found["max"] = float(np.min(values)), float(np.max(values))
    return found


def mean_text(mean: float, digits: int, whole: bool) -> str:
    """The mean, with one more decimal when the variable holds whole numbers."""
    if math.isnan(mean):
        return EMPTY
    return format_number(round(mean, SNAP_DIGITS), digits + (1 if whole else 0))


def summary_text(found: dict, stat: str, digits: int, whole: bool = False) -> str:
    """One statistic as text from summary_numbers(); `whole` (the variable holds whole numbers) gives means one more
    decimal."""
    if stat == "n_missing":
        return format_number(found["missing"], 0)
    if not found["n"]:
        return EMPTY

    def number(value: float) -> str:
        # Snap away float noise first: R and numpy reach the same quantile by different arithmetic.
        return format_number(round(value, SNAP_DIGITS), quantile_places(value, digits, whole))
    if stat == "median_iqr":
        return f"{number(found['median'])} ({number(found['q1'])}{EMPTY}{number(found['q3'])})"
    if stat == "mean_sd":
        places = digits + (1 if whole else 0)
        return f"{mean_text(found['mean'], digits, whole)} ({format_number(round(found['sd'], SNAP_DIGITS), places)})"
    return f"{number(found['min'])}{EMPTY}{number(found['max'])}"


def count_share(count: int, total: int) -> str:
    """'42 (23.3%)'; the share of the non-missing values in that column."""
    share = format_percent(count / total, load_tokens()["study"]["percent_digits"]) if total else EMPTY
    return f"{format_number(count, 0)} ({share})"


def share_of(count: int, total: int) -> float:
    return count / total if total else math.nan


MISSING_NOUNS = {"variable": "a value", "group": "a group", "date": "a date"}


def listed(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def left_out_text(rows: dict, unit: str, roles: tuple[str, ...] = ("variable", "group", "date")) -> str:
    """' 39 of 40 participants; 1 without a value was left out.' from a result's rows, for the `roles` whose
    missing rows left the analysis; empty when none did."""
    counts = {role: count for role, count in rows["missing"].items() if count and role in roles}
    if not counts:
        return ""
    parts = [f"{format_number(count, 0)} without {MISSING_NOUNS[role]}" for role, count in counts.items()]
    verb = "was" if sum(counts.values()) == 1 else "were"
    return (f" {format_number(rows['analysed'], 0)} of {format_number(rows['total'], 0)} {unit}; {listed(parts)} "
            f"{verb} left out.")


def overall_only_text(rows: dict) -> str:
    """' 1 without a group is counted in Overall only.'; empty when every row has a group."""
    count = rows["missing"].get("group", 0)
    if not count:
        return ""
    return f" {format_number(count, 0)} without a group {'is' if count == 1 else 'are'} counted in Overall only."
