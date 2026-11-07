"""Spread rows: per group the range as a thin line, the interquartile range as a band in the group's colour, the
median as a dot, an optional reference tick, and the key numbers in a column on the right."""

from __future__ import annotations

import math
import numbers
import warnings
from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from hairline.charts.common import (
    check_columns,
    check_numeric,
    clip_caption,
    clip_limits,
    coarse_groups,
    drop_small,
    humanise,
    series_colors,
    with_caption,
    within,
)
from hairline.charts.forest import decimals
from hairline.charts.spread_geometry import spread_drawing
from hairline.charts.timeseries import groups_of
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
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
from hairline.settings import current_settings
from hairline.stats.density import level_quantiles, median_gap, quantiles, top_levels
from hairline.ticks import axis_limits, nice_breaks
from hairline.tokens import load_tokens

STATS = ("median", "iqr", "mean", "n", "range", "levels")
SORTS = (None, "median")
DASH = "–"


def number_formatter(values: np.ndarray, percent: bool, digits: int | None, extra: int = 0):
    """Formats values with digits by magnitude (of the percentage for shares), plus `extra` decimals (one for
    means of whole numbers); float noise snapped first."""
    scale = 100.0 if percent else 1.0
    places = (digits if digits is not None else auto_digits(values * scale)) + extra
    suffix = locale_symbols(None)["percent_space"] + "%" if percent else ""
    return lambda value: format_number(snap_noise(float(value) * scale), places) + suffix


def levels_text(values: np.ndarray, number) -> str:
    """The most frequent values with their shares: '25 (48 %) · 50 (41 %)'."""
    shown = top_levels(values, load_tokens()["spread"]["levels_shown"])
    return " · ".join(f"{number(level)} ({format_percent(share, 0)})" for level, share in shown)


def stats_pairs(values: np.ndarray, stats: Sequence[str], numbers: tuple, mark: float | None,
                mark_label: str | None, discrete: bool = False) -> list[list[str]]:
    """Key numbers as (label, value) pairs, drawn like a panel header's key numbers."""
    number, mean_number = numbers
    low, q1, middle, q3, high = (level_quantiles if discrete else quantiles)(values, [0, 0.25, 0.5, 0.75, 1])
    parts = {"median": ["Median", number(middle)], "iqr": ["IQR", f"{number(q1)}{DASH}{number(q3)}"],
             "mean": ["Mean", mean_number(np.mean(values))], "n": ["n", format_number(len(values), 0)],
             "range": ["Range", f"{number(low)}{DASH}{number(high)}"],
             "levels": [word("levels"), levels_text(values, number)] if "levels" in stats else None}
    pairs = [parts[name] for name in stats]
    if mark is not None and mark_label:
        pairs.append([mark_label, number(mark)])
    return pairs


def check_options(stats: str | Sequence[str], digits: int | None) -> tuple[str, ...]:
    """The statistics to show, each once ("median" alone is one statistic), and decimals as a whole number."""
    stats = (stats,) if isinstance(stats, str) else tuple(stats)
    unknown = [name for name in stats if name not in STATS]
    if unknown:
        raise ValueError(f"hairline: spread: unknown statistic {unknown[0]!r}; use any of {', '.join(STATS)}")
    repeated = next((name for name in stats if stats.count(name) > 1), None)
    if repeated:
        raise ValueError(f"hairline: spread: stats names {repeated!r} twice; name each statistic once")
    if digits is not None and (isinstance(digits, bool) or not isinstance(digits, int) or digits < 0):
        raise ValueError(f"hairline: spread: digits must be a whole number of 0 or more; got {digits!r}")
    return stats


def checked_marks(marks: Mapping[str, float] | None, groups: list[tuple[str, np.ndarray]]) -> dict[str, float]:
    """Reference values for groups that are drawn, as finite numbers: a mistyped group would lose its tick."""
    marks, names = {str(name): value for name, value in (marks or {}).items()}, [name for name, _ in groups]
    for name, value in marks.items():
        if name not in names:
            raise ValueError(f"hairline: spread: marks names '{name}', which is not a group drawn; groups: "
                             f"{', '.join(names)}")
        if isinstance(value, bool) or not isinstance(value, numbers.Real) or not math.isfinite(value):
            raise ValueError(f"hairline: spread: the mark for '{name}' is {value!r}; marks are finite numbers")
    return marks


def spread_axis(lows: list[float], highs: list[float], percent: bool, zero: bool) -> dict:
    low, high = min(lows + ([0.0] if zero else [])), max(highs + ([0.0] if zero else []))
    breaks = nice_breaks(low, high)
    limits = axis_limits(low, high, breaks)
    shown = [value * (100 if percent else 1) for value in breaks]
    places = decimals([snap_noise(value) for value in shown])
    labels = [format_number(snap_noise(value), places) for value in shown]
    if percent:
        labels[-1] += locale_symbols(None)["percent_space"] + "%"
    return {"breaks": breaks, "labels": labels, "low": limits[0], "high": limits[1]}


def level_number(value: float) -> str:
    """A level as given: 12.5 mg stays 12.5 and 50 stays 50 (up to three decimals). On discrete data a rounded
    level would read as a dose nobody gave."""
    from hairline.figure import exact_places
    value = snap_noise(float(value))
    return format_number(value, min(3, exact_places(value)))


def warn_median_gaps(groups: list[tuple[str, np.ndarray]], numbers: tuple, chart: str = "spread") -> None:
    # The median takes one more decimal for whole numbers (37.5, not the 38 the column shows); levels as they are.
    """A median between two levels that each hold a large share matches neither (doses of 25 and 50 mg, median
    35): say so, as a report would need a footnote for it."""
    share, least = load_tokens()["spread"]["discrete_share"], load_tokens()["spread"]["discrete_min_n"]
    for name, values in groups:
        gap = median_gap(values, share, least)
        if gap is not None:
            label = f" of '{name}'" if name else ""
            number, median = numbers
            warnings.warn(f"hairline: {chart}: the median{label}, {median(float(np.median(values)))}, lies between "
                          f"{number(gap[0])} and {number(gap[1])}, which each hold more than {format_percent(share, 0)}"
                          f" of the values, and matches neither; show stats=('levels', ...) or use discrete=True",
                          UserWarning, stacklevel=4)


def arranged(rows: list[dict], sort: str | None) -> list[dict]:
    """Rows by section (in the order sections first appear), then by median, highest first, when sorted."""
    sections = list(dict.fromkeys(row["section"] for row in rows))
    ordered = sorted(rows, key=lambda row: sections.index(row["section"]))
    if sort == "median":
        ordered = sorted(ordered, key=lambda row: (sections.index(row["section"]), -row["median"]))
    return ordered


def spread_spec(data: pd.DataFrame, group: str, value: str, *, order: Sequence[str] | None = None,
                marks: Mapping[str, float] | None = None, mark_label: str | None = None,
                stats: Sequence[str] = ("median", "iqr", "mean"), percent: bool = False, digits: int | None = None,
                zero: bool = False, axis_title: str | None = None, colors: Mapping[str, str] | None = None,
                show_n: bool = False, min_n: int | None = None,
                clip: float | tuple[float | None, float | None] | None = None, clip_stats: bool = False,
                color_by: str | None = None, dimension: str | None = None, discrete: bool = False,
                section: str | None = None, panel_letters: bool = False, mean: bool = False,
                sort: str | None = None) -> dict:
    check_columns(data, [group, value, color_by, section])
    if sort not in SORTS:
        raise ValueError(f"hairline: spread: sort {sort!r} must be 'median' or None")
    check_numeric(data, [value], "spread")
    stats = check_options(stats, digits)
    if show_n and "n" not in stats:
        stats = (*stats, "n")
    locale = current_settings().locale
    groups = [(str(name), rows[value].dropna().astype(float).to_numpy())
              for name, rows in groups_of(data, group, order, "spread")]
    groups = [(name, values) for name, values in groups if len(values)]
    if not groups:
        raise ValueError(f"hairline: spread: no values to draw; '{value}' is empty or missing in every row")
    groups, small = drop_small(groups, min_n, "spread", locale)
    every = np.concatenate([values for _, values in groups])
    limits = clip_limits(every, clip, "spread")
    drawn = [(name, within(values, limits)) for name, values in groups]
    if not all(len(values) for _, values in drawn):
        empty = next(name for name, values in drawn if not len(values))
        raise ValueError(f"hairline: spread: clip hides every value of '{empty}'; widen the limits")
    counted = drawn if clip_stats else groups
    whole = is_whole(every) and not percent
    plain, mean_number = number_formatter(every, percent, digits), number_formatter(every, percent, digits,
                                                                                    1 if whole else 0)
    whole = whole and digits is None and not discrete
    # Of whole numbers, a quantile between two of them keeps one decimal (a median of 2.5, not 3).
    numbers = ((lambda value: mean_number(value) if quantile_places(value, 0, whole) else plain(value)), mean_number)
    if discrete and digits is None and not percent:
        numbers = (level_number, mean_number)
    if not discrete:
        warn_median_gaps(counted, numbers)
    names = [name for name, _ in groups]
    palette, coarse = series_colors(names, data, group, color_by, colors, dimension, "spread")
    marks = checked_marks(marks, groups)
    sections = coarse_groups(data, group, section, "spread") if section else {}
    rows = []
    for (name, values), (_, shown) in zip(counted, drawn, strict=True):
        q1, middle, q3 = (level_quantiles if discrete else quantiles)(values, [0.25, 0.5, 0.75])
        low, high = float(shown.min()), float(shown.max())
        mark = marks.get(name)
        rows.append({"name": name, "color": palette[name], "low": low, "q1": min(max(q1, low), high),
                     "median": min(max(middle, low), high), "q3": min(max(q3, low), high), "high": high,
                     "mark": None if mark is None else float(mark),
                     "mean": min(max(float(np.mean(values)), low), high) if mean else None,
                     "section": sections[name] if section else None,
                     "pairs": stats_pairs(values, stats, numbers, mark, mark_label, discrete)})
    rows = arranged(rows, sort)
    lows = [row["low"] for row in rows] + [row["mark"] for row in rows if row["mark"] is not None]
    highs = [row["high"] for row in rows] + [row["mark"] for row in rows if row["mark"] is not None]
    notes = [small, clip_caption(every, limits, clip_stats, locale) if clip is not None else None,
             word("levels_note", locale) if discrete else None]
    legend = [("square", color, label) for label, color in dict.fromkeys((coarse[name], palette[name])
                                                                           for name in names)] if color_by else []
    if mean:
        ink = current_settings().neutral["ink"]
        legend += [("dot", ink, word("median", locale)), ("diamond", ink, word("mean", locale))]
    return {"rows": rows, "axis": spread_axis(lows, highs, percent, zero), "axis_title": axis_title,
            "notes": [note for note in notes if note], "legend": legend, "letters": panel_letters}


def spread(data: pd.DataFrame, group: str, value: str, *, title: str | None = None, subtitle: str | None = None,
           caption: str | None = None, order: Sequence[str] | None = None, marks: Mapping[str, float] | None = None,
           mark_label: str | None = None, stats: Sequence[str] = ("median", "iqr", "mean"), percent: bool = False,
           digits: int | None = None, zero: bool = False, axis_title: str | None = None,
           colors: Mapping[str, str] | None = None, size: str = "onehalf", show_n: bool = False,
           min_n: int | None = None, clip: float | tuple[float | None, float | None] | None = None,
           clip_stats: bool = False, color_by: str | None = None, dimension: str | None = None,
           discrete: bool = False, section: str | None = None, panel_letters: bool = False, mean: bool = False,
           sort: str | None = None) -> HairlineFigure:
    """Distributions per group compared on one axis, first group on top; `marks` adds a reference tick per group
    (a capacity, a target), `mark_label` names it in the numbers column; `axis_title` (e.g. the unit) goes under
    the axis numbers. On a figure too narrow for the numbers beside the plot, they sit on a line under each row.

    `show_n` adds each group's n to the numbers column. `min_n` leaves out groups with fewer values and names them
    in the caption. `clip` hides implausible values (0.99: above the 99th percentile of every value; (low, high):
    outside those values) and says in the caption how many and where; the statistics still use every value unless
    `clip_stats`. `stats` may include "levels", the most frequent values with their shares; a median that falls
    between two large levels is warned about. `discrete` keeps quantiles on the data's levels (whole people, whole
    doses). `color_by` colours the rows by a coarser column, `dimension` keeps them off another dimension's slots.

    `section` draws the rows in blocks of that column, each under its name (lettered a, b, c with
    `panel_letters`) on one shared axis; `sort="median"` orders the rows of a block by median, highest first;
    `mean` marks each row's mean as an open diamond, and the legend row names median and mean."""
    spec = spread_spec(data, group, value, order=order, marks=marks, mark_label=mark_label, stats=stats,
                       percent=percent, digits=digits, zero=zero, axis_title=axis_title, colors=colors,
                       show_n=show_n, min_n=min_n, clip=clip, clip_stats=clip_stats, color_by=color_by,
                       dimension=dimension, discrete=discrete, section=section, panel_letters=panel_letters,
                       mean=mean, sort=sort)
    result = figure(title or f"{humanise(value)} by {str(group).replace('_', ' ')}", subtitle=subtitle,
                    caption=with_caption(caption, *spec["notes"]), size=size)
    result.draw(0, lambda box, measure, style: spread_drawing(spec, box, measure, style))
    if spec["legend"]:
        result.legend(spec["legend"])
    return fit_height(result)
