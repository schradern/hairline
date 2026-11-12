"""summary= and stats=: the measures distribution charts draw and write, named the same on every chart and in both
languages. `summary` chooses the marks (the median, the mean as an open diamond, the IQR as a thick bar, the range as
a thin line, the SD or 95 % CI of the mean as a slim bar); `stats` writes the same measures as numbers. The R
package mirrors this in summaries.R."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

import numpy as np

from hairline.numbers import (
    auto_digits,
    format_number,
    format_percent,
    is_whole,
    locale_symbols,
    quantile_places,
    snap_noise,
    word,
)
from hairline.stats.density import level_quantiles, quantiles, top_levels
from hairline.stats.distributions import t_quantile
from hairline.tokens import load_tokens

SUMMARY_NAMES = ("median", "mean", "iqr", "range", "sd", "ci")
CENTRES = ("median", "mean")
# Interval bars: each sits in the same place, so a chart draws one of them.
BARS = ("iqr", "sd", "ci")
STAT_NAMES = (*SUMMARY_NAMES, "n")
# The centre an interval belongs to, where a chart draws one centre with one interval (dot plot, time series).
PAIRED = {"iqr": "median", "sd": "mean", "ci": "mean"}
CI_LEVEL = 0.95
DASH = "–"
LEGEND_KINDS = {"mean": "diamond", "iqr": "bar", "range": "thin", "sd": "slim", "ci": "slim"}
LEGEND_WORDS = {"median": "median", "mean": "mean", "iqr": "iqr", "range": "range", "sd": "sd_bar", "ci": "ci"}

Numbers = tuple[Callable[[float], str], Callable[[float], str]]


def as_names(value: str | Sequence[str], chart: str, option: str, allowed: Sequence[str]) -> tuple[str, ...]:
    """Names as a tuple ("median" alone is one name), each known and given once."""
    names = (value,) if isinstance(value, str) else tuple(value)
    unknown = [name for name in names if name not in allowed]
    if unknown:
        raise ValueError(f"hairline: {chart}: unknown {option} {unknown[0]!r}; use any of {', '.join(allowed)}")
    repeated = next((name for name in names if names.count(name) > 1), None)
    if repeated:
        raise ValueError(f"hairline: {chart}: {option} names {repeated!r} twice; name each once")
    return names


def check_summary(summary: str | Sequence[str], chart: str, allowed: Sequence[str] = SUMMARY_NAMES,
                  why: str = "") -> tuple[str, ...]:
    """The summary marks to draw: known names, each once, those the chart draws, and one interval bar at most."""
    names = as_names(summary, chart, "summary", SUMMARY_NAMES)
    refused = [name for name in names if name not in allowed]
    if refused:
        raise ValueError(f"hairline: {chart}: summary {refused[0]!r} is not drawn here; {chart} draws "
                         f"{', '.join(allowed)}{'. ' + why if why else ''}")
    bars = [name for name in names if name in BARS]
    if len(bars) > 1:
        raise ValueError(f"hairline: {chart}: summary {bars[0]!r} and {bars[1]!r} would draw two bars in one place; "
                         f"give one of {', '.join(BARS)}")
    return names


def check_paired(names: Sequence[str], chart: str) -> tuple[str, str | None]:
    """One centre and at most one interval that belongs to it (the IQR to the median, the SD and CI to the mean;
    the range to either), for charts that draw a centre with its interval."""
    centres = [name for name in names if name in CENTRES]
    intervals = [name for name in names if name not in CENTRES]
    if len(centres) != 1:
        raise ValueError(f"hairline: {chart}: summary needs one centre, 'median' or 'mean'; got "
                         f"{', '.join(map(repr, centres)) or 'none'}")
    if len(intervals) > 1:
        raise ValueError(f"hairline: {chart}: summary draws one interval with its centre; got "
                         f"{', '.join(map(repr, intervals))}")
    interval = intervals[0] if intervals else None
    needed = PAIRED.get(interval or "")
    if needed and needed != centres[0]:
        raise ValueError(f"hairline: {chart}: {interval!r} goes with the {needed}; use summary=('{needed}', "
                         f"'{interval}')")
    return centres[0], interval


def summary_values(values: Sequence[float], discrete: bool = False) -> dict:
    """Every measure of `values`: n, range, quartiles (on the data's levels when `discrete`), mean, SD and the 95 %
    CI of the mean (t distribution); SD and CI are NaN below two values."""
    data = np.asarray(values, dtype=float)
    low, q1, middle, q3, high = (level_quantiles if discrete else quantiles)(data, [0, 0.25, 0.5, 0.75, 1])
    count, mean = len(data), float(np.mean(data))
    sd = float(np.std(data, ddof=1)) if count > 1 else math.nan
    half = t_quantile(1 - (1 - CI_LEVEL) / 2, count - 1) * sd / math.sqrt(count) if count > 1 else math.nan
    return {"n": count, "low": low, "q1": q1, "median": middle, "q3": q3, "high": high, "mean": mean, "sd": sd,
            "ci_low": mean - half, "ci_high": mean + half}


def interval_of(found: dict, name: str) -> tuple[float, float]:
    """An interval's ends from summary_values()."""
    if name == "iqr":
        return found["q1"], found["q3"]
    if name == "range":
        return found["low"], found["high"]
    if name == "sd":
        return found["mean"] - found["sd"], found["mean"] + found["sd"]
    return found["ci_low"], found["ci_high"]


def number_formatter(values: np.ndarray, percent: bool, digits: int | None, extra: int = 0) -> Callable[[float], str]:
    """Formats values with digits by magnitude (of the percentage for shares), plus `extra` decimals (one for means
    of whole numbers); float noise snapped first."""
    scale = 100.0 if percent else 1.0
    places = (digits if digits is not None else auto_digits(values * scale)) + extra
    suffix = locale_symbols(None)["percent_space"] + "%" if percent else ""
    return lambda value: format_number(snap_noise(float(value) * scale), places) + suffix


def level_number(value: float) -> str:
    """A level as given: 12.5 mg stays 12.5 and 50 stays 50 (up to three decimals). On discrete data a rounded level
    would read as a dose nobody gave."""
    from hairline.figure import exact_places
    value = snap_noise(float(value))
    return format_number(value, min(3, exact_places(value)))


def measure_numbers(every: np.ndarray, percent: bool, digits: int | None, discrete: bool = False) -> Numbers:
    """Formatters for quantiles and for means. Of whole numbers a mean takes one more decimal, and a quantile
    between two of them keeps one (a median of 2.5, not 3); on discrete data quantiles are levels as given."""
    whole = is_whole(every) and not percent
    plain = number_formatter(every, percent, digits)
    mean_number = number_formatter(every, percent, digits, 1 if whole else 0)
    if discrete and digits is None and not percent:
        return level_number, mean_number
    halves = whole and digits is None

    def number(value: float) -> str:
        return mean_number(value) if quantile_places(value, 0, halves) else plain(value)
    return number, mean_number


def levels_text(values: np.ndarray, number: Callable[[float], str]) -> str:
    """The most frequent values with their shares: '25 (48 %) · 50 (41 %)'."""
    shown = top_levels(values, load_tokens()["spread"]["levels_shown"])
    return " · ".join(f"{number(level)} ({format_percent(share, 0)})" for level, share in shown)


def stat_label(name: str, locale: str | None = None) -> str:
    return "n" if name == "n" else word(name, locale)


def stat_text(name: str, found: dict, numbers: Numbers, values: np.ndarray, locale: str | None = None) -> str:
    number, mean_number = numbers
    if name == "n":
        return format_number(found["n"], 0, locale)
    if name == "levels":
        return levels_text(values, number)
    if name in ("sd", "ci") and not math.isfinite(found["sd"]):
        return DASH
    if name == "median":
        return number(found["median"])
    if name in ("mean", "sd"):
        return mean_number(found[name])
    low, high = interval_of(found, name)
    shown = mean_number if name == "ci" else number
    return f"{shown(low)}{DASH}{shown(high)}"


def stat_pairs(values: Sequence[float], names: Sequence[str], numbers: Numbers, discrete: bool = False,
               locale: str | None = None) -> list[list[str]]:
    """The measures as (label, value) pairs, drawn like a panel header's key numbers: 'Median 12', 'IQR 9–15'."""
    data = np.asarray(values, dtype=float)
    found = summary_values(data, discrete)
    return [[stat_label(name, locale), stat_text(name, found, numbers, data, locale)] for name in names]


def summary_legend(names: Sequence[str], median_kind: str, color: str, locale: str | None = None) -> list[tuple]:
    """Legend items naming each mark drawn, in the order given, in one colour (the groups keep theirs)."""
    kinds = {**LEGEND_KINDS, "median": median_kind}
    return [(kinds[name], color, word(LEGEND_WORDS[name], locale)) for name in names]
