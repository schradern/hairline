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
from hairline.charts.comparisons import section_comparisons
from hairline.charts.forest import decimals
from hairline.charts.options import (
    FACET_BLOCK,
    FACET_KEY,
    Reference,
    add_reference_legend,
    check_numbers,
    facet_rows,
    legend_references,
    references,
)
from hairline.charts.spread_geometry import spread_drawing
from hairline.charts.summaries import (
    BARS,
    Numbers,
    check_summary,
    interval_of,
    measure_numbers,
    stat_pairs,
    summary_legend,
    summary_values,
)
from hairline.charts.timeseries import groups_of
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.numbers import (
    format_number,
    format_percent,
    locale_symbols,
    snap_noise,
    word,
)
from hairline.settings import current_settings
from hairline.stats.density import median_gap
from hairline.ticks import axis_limits, nice_breaks
from hairline.tokens import load_tokens

STATS = ("median", "iqr", "mean", "n", "range", "levels", "sd", "ci")
SORTS = (None, "median")
DEFAULT_SUMMARY = ("median", "iqr", "range")


def stats_pairs(values: np.ndarray, stats: Sequence[str], numbers: Numbers, mark: float | None,
                mark_label: str | None, discrete: bool = False) -> list[list[str]]:
    """Key numbers as (label, value) pairs, drawn like a panel header's key numbers, the group's mark last."""
    pairs = stat_pairs(values, stats, numbers, discrete)
    if mark is not None and mark_label:
        pairs.append([mark_label, numbers[0](mark)])
    return pairs


def summary_row(values: np.ndarray, shown: np.ndarray, names: Sequence[str], discrete: bool) -> dict:
    """A row's marks: the range of the values drawn, the quartiles and mean held within it, and the interval bar
    (an SD or CI may reach past the values drawn; the axis widens for it)."""
    found = summary_values(values, discrete)
    low, high = float(shown.min()), float(shown.max())

    def held(value: float) -> float:
        return min(max(value, low), high)
    bar = next((name for name in names if name in BARS), None)
    ends = None
    if bar == "iqr":
        ends = (held(found["q1"]), held(found["q3"]), False)
    elif bar and math.isfinite(found["sd"]):
        ends = (*interval_of(found, bar), True)
    return {"low": low, "high": high, "range": "range" in names, "bar": ends, "median": held(found["median"]),
            "show_median": "median" in names, "mean": held(found["mean"]) if "mean" in names else None}


def chosen_summary(summary: str | Sequence[str] | None, mean: bool) -> tuple[str, ...]:
    """The marks drawn: the default (median dot, IQR band, range line) or `summary`, with the mean when `mean`."""
    names = DEFAULT_SUMMARY if summary is None else check_summary(summary, "spread")
    return (*names, "mean") if mean and "mean" not in names else names


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
                sort: str | None = None, reference: Reference = None,
                highlight: Sequence[str] | str | None = None, summary: str | Sequence[str] | None = None,
                compare: str | None = None, group_names: Mapping[str, str] | None = None) -> dict:
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
    numbers = measure_numbers(every, percent, digits, discrete)
    drawn_marks = chosen_summary(summary, mean)
    if not discrete:
        warn_median_gaps(counted, numbers)
    names = [name for name, _ in groups]
    palette, coarse = series_colors(names, data, group, color_by, colors, dimension, "spread", highlight,
                                    named=True)
    lines = references(reference, "spread")
    marks = checked_marks(marks, groups)
    sections = coarse_groups(data, group, section, "spread") if section else {}
    rows = []
    for (name, values), (_, shown) in zip(counted, drawn, strict=True):
        mark = marks.get(name)
        rows.append({**summary_row(values, shown, drawn_marks, discrete), "name": name, "color": palette[name],
                     "mark": None if mark is None else float(mark), "section": sections[name] if section else None,
                     "pairs": stats_pairs(values, stats, numbers, mark, mark_label, discrete)})
    rows = arranged(rows, sort)
    extra = [row["mark"] for row in rows if row["mark"] is not None] + [value for value, _ in lines] + \
        [end for row in rows if row["bar"] for end in row["bar"][:2]]
    lows, highs = [row["low"] for row in rows] + extra, [row["high"] for row in rows] + extra
    notes = [small, clip_caption(every, limits, clip_stats, locale) if clip is not None else None,
             word("levels_note", locale) if discrete else None,
             section_comparisons(rows, dict(counted), compare, drawn_marks, numbers, "spread", group_names)]
    legend = [("square", color, label) for label, color in dict.fromkeys((coarse[name], palette[name])
                                                                           for name in names)] if color_by else []
    if summary is not None or mean:
        # mean=True alone names the two centres, as it always has; a summary names every mark it draws.
        named = drawn_marks if summary is not None else ("median", "mean")
        legend += summary_legend(named, "dot", current_settings().neutral["ink"], locale)
    return {"rows": rows, "axis": spread_axis(lows, highs, percent, zero), "axis_title": axis_title,
            "notes": [note for note in notes if note], "legend": legend, "letters": panel_letters,
            "references": [list(line) for line in lines]}


def spread(data: pd.DataFrame, group: str, value: str, *, title: str | None = None, subtitle: str | None = None,
           caption: str | None = None, order: Sequence[str] | None = None, marks: Mapping[str, float] | None = None,
           mark_label: str | None = None, stats: Sequence[str] = ("median", "iqr", "mean"), percent: bool = False,
           digits: int | None = None, zero: bool = False, axis_title: str | None = None,
           colors: Mapping[str, str] | None = None, size: str = "onehalf", show_n: bool = False,
           min_n: int | None = None, clip: float | tuple[float | None, float | None] | None = None,
           clip_stats: bool = False, color_by: str | None = None, dimension: str | None = None,
           discrete: bool = False, section: str | None = None, panel_letters: bool = False, mean: bool = False,
           sort: str | None = None, x_title: str | None = None, reference: Reference = None,
           reference_legend: bool = False, highlight: Sequence[str] | str | None = None, key_title: str | None = None,
           facet: str | None = None, summary: str | Sequence[str] | None = None,
           compare: str | None = None, numbers: str = "auto") -> HairlineFigure:
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
    `mean` marks each row's mean as an open diamond, and the legend row names median and mean.

    Shared with the other charts: `x_title` (the same as `axis_title`), `reference` (dashed lines across the rows,
    labelled above them or, with `reference_legend`, in the legend row), `highlight` (groups kept in colour),
    `key_title` and `facet` (a block of rows per value of that column, under its name, on the one axis; a group keeps
    its colour in every block).

    `compare` writes each row's difference against one group (compare="Unit A") or the row above ("adjacent"),
    with its 95 % CI and p, beside the other numbers (within each block); the caption names the test, which follows
    the centre: the Hodges–Lehmann shift and Wilcoxon rank-sum test with the median, the difference in means and
    Welch's t-test with the mean alone. `numbers` places the numbers: beside the plot while it keeps its least
    width, else under each row ("auto"), always beside it ("right"), or always under each row ("below")."""
    reference, legend_labels = legend_references(reference, reference_legend, "spread")
    if facet is not None:
        spec = faceted_spec(data, group, value, facet, order=order, marks=marks, mark_label=mark_label, stats=stats,
                            percent=percent, digits=digits, zero=zero, axis_title=axis_title or x_title,
                            colors=colors, show_n=show_n, min_n=min_n, clip=clip, clip_stats=clip_stats,
                            color_by=color_by, dimension=dimension, discrete=discrete, section=section,
                            panel_letters=panel_letters, mean=mean, sort=sort, reference=reference,
                            highlight=highlight, summary=summary, compare=compare)
    else:
        spec = spread_spec(data, group, value, order=order, marks=marks, mark_label=mark_label, stats=stats,
                           percent=percent, digits=digits, zero=zero, axis_title=axis_title or x_title, colors=colors,
                           show_n=show_n, min_n=min_n, clip=clip, clip_stats=clip_stats, color_by=color_by,
                           dimension=dimension, discrete=discrete, section=section, panel_letters=panel_letters,
                           mean=mean, sort=sort, reference=reference, highlight=highlight, summary=summary,
                           compare=compare)
    spec["numbers"] = check_numbers(numbers, "spread")
    result = figure(title or f"{humanise(value)} by {str(group).replace('_', ' ')}", subtitle=subtitle,
                    caption=with_caption(caption, *spec["notes"]), size=size)
    result.draw(0, lambda box, measure, style: spread_drawing(spec, box, measure, style))
    if spec["legend"]:
        result.legend(spec["legend"])
    add_reference_legend(result, legend_labels)
    result.key_title(key_title)
    return fit_height(result)


def faceted_spec(data: pd.DataFrame, group: str, value: str, facet: str, **options) -> dict:
    """spread_spec() with a block of rows per value of `facet`: every row keyed by facet and group, the blocks drawn
    as sections, each group in its own colour in every block (as `colors`), names shown without the facet."""
    if options.pop("section") is not None:
        raise ValueError("hairline: spread: facet and section both draw blocks of rows; give one of them")
    keyed, keys, groups = facet_rows(data, group, facet, options.pop("order"), "spread")
    names = list(dict.fromkeys(groups.values()))
    palette, coarse = series_colors(names, data, group, options.pop("color_by"), options.pop("colors"),
                                    options.pop("dimension"), "spread", options.pop("highlight"), named=True)
    marks = options.pop("marks") or {}
    spec = spread_spec(keyed, FACET_KEY, value, order=keys, section=FACET_BLOCK, group_names=groups,
                       colors={key: palette[groups[key]] for key in keys},
                       marks={key: marks[groups[key]] for key in keys if groups[key] in marks} or None, **options)
    for row in spec["rows"]:
        row["name"] = groups[row["name"]]
    legend = [entry for entry in spec["legend"] if entry[0] != "square"]
    squares = [("square", palette[name], coarse[name]) for name in names] if coarse != {n: n for n in names} else []
    spec["legend"] = list(dict.fromkeys(squares)) + legend
    return spec
