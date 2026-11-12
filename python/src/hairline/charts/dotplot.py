"""Dot plot with intervals: sorted by value, labels on the left, the value on the right."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import pandas as pd

from hairline.charts.common import (
    check_columns,
    check_labels,
    check_numeric,
    drop_small,
    humanise,
    labels_with_n,
    ordered_names,
    with_caption,
)
from hairline.charts.comparisons import section_comparisons
from hairline.charts.forest import forest_spec
from hairline.charts.forest_geometry import forest_drawing
from hairline.charts.options import (
    Reference,
    add_reference_legend,
    check_numbers,
    checked_highlight,
    legend_references,
    references,
)
from hairline.charts.summaries import LEGEND_WORDS, check_paired, check_summary, interval_of, summary_values
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.marks import context_color, lone_color
from hairline.numbers import auto_digits, format_number, is_whole, word
from hairline.settings import current_settings

SUMMARY_LOW, SUMMARY_HIGH, SUMMARY_N = "_hairline_low", "_hairline_high", "_hairline_n"


def dotplot(data: pd.DataFrame, label: str, estimate: str, low: str | None = None, high: str | None = None, *,
            title: str | None = None, subtitle: str | None = None, caption: str | None = None, sort: bool = True,
            ratio: bool = False, reference: Reference = None, reference_legend: bool = False,
            digits: int | None = None,
            size: str = "onehalf", n: str | None = None, percent: bool = False, order: Sequence[str] | None = None,
            min_n: int | None = None, x_title: str | None = None,
            highlight: Sequence[str] | str | None = None, facet: str | None = None,
            show_n: bool = True, summary: str | Sequence[str] | None = None,
            compare: str | None = None, numbers: str = "auto") -> HairlineFigure:
    """One dot per row, largest at the top; with `low` and `high` an interval and its numbers on the right.
    `n` names the column holding each row's n, written after its label in the locale ("Medical (n = 1,010)").
    `percent=True` draws shares (0.15) as percent (15), the heading naming the unit. `order` gives the rows'
    order instead of sorting by value. `show_n=False` leaves the n out of the labels (it still counts for `min_n`).

    Shared with the other charts: `reference` draws dashed lines (a target, a null value: 0.1, (0.1, "Target") or
    {"Target": 0.1}; `reference_legend` names the label in the legend row); `min_n` leaves out rows whose `n` is smaller
    and names them; `x_title` titles the axis; `highlight` keeps these rows in colour; `facet` draws a block of rows per
    value of that column under its name, on the one axis, each block sorted on its own.

    `summary` takes the rows as values and draws one row per label (per block with `facet`): a centre, "median"
    or "mean", with an interval that belongs to it, "iqr" or "range" with the median, "sd", "ci" or "range" with
    the mean (summary=("mean", "ci")). Each row's n is counted, written after its label and used by `min_n`; the
    heading names the measures and the axis takes the column's name. With `summary`, `compare` adds columns with
    each row's difference against one label (compare="Medical") or the row above ("adjacent"), its 95 % CI and p,
    within each block; the caption names the test (Welch's t-test with the mean, the Hodges–Lehmann shift and
    Wilcoxon rank-sum test with the median).

    `numbers` places the numbers: beside the intervals while they keep their least width, else under each row
    ("auto"), always beside them ("right"), or always under each row ("below")."""
    check_columns(data, [label, estimate, low, high, n, facet])
    if (low is None) != (high is None):
        raise ValueError(f"hairline: dotplot: an interval needs both low and high; got only "
                         f"{'low' if low is not None else 'high'}={low if low is not None else high!r}")
    data = as_percent(data, [estimate, low, high]) if percent else data
    heading, raw = None, data
    if compare is not None and summary is None:
        raise ValueError("hairline: dotplot: compare needs summary=, so each row has the values it is compared on "
                         "(summary=('mean', 'ci'))")
    if summary is not None:
        # Decimals as the other charts write a mean of these values: by magnitude, one more for whole numbers.
        values = pd.to_numeric(data[estimate], errors="coerce").dropna().to_numpy(dtype=float)
        digits = digits if digits is not None else auto_digits(values) + (1 if is_whole(values) else 0)
        data, low, high, n, heading = summarised(data, label, estimate, (low, high, n), facet, summary)
        x_title = x_title or (f"{humanise(estimate)} (%)" if percent else humanise(estimate))
    interval = low is not None and high is not None
    data, small = rows_with_min_n(data, label, n, min_n)
    rows, blocks = faceted_rows(data, label, estimate, sort, order, facet)
    names = [str(name) for name in rows[label]]
    rows, columns, compared = dot_comparisons(raw, rows, names, blocks, (label, estimate, facet), compare, summary,
                                              digits)
    chosen = checked_highlight(highlight, names, "dotplot")
    drawn_references, legend_labels = legend_references(reference, reference_legend, "dotplot")
    if n is not None:
        check_numeric(rows, [n], "dotplot")
    if n is not None and show_n:
        rows = rows.assign(**{label: labels_with_n(names, dict(zip(names, rows[n], strict=True)),
                                                    current_settings().locale)})
    if not interval:
        rows = rows.assign(_low=rows[estimate], _high=rows[estimate])
        low, high = "_low", "_high"
    name = f"{humanise(estimate)} (%)" if percent else humanise(estimate)
    heading = heading or (word("interval", name=name) if interval else name)
    spec = forest_spec(rows, label, estimate, low, high, ratio=ratio, color=lone_color(),
                       study_heading=humanise(label), effect_heading=heading, digits=digits, marker="dot",
                       columns=columns, numbers=check_numbers(numbers, "dotplot"),
                       interval=interval, null=None, references=references(drawn_references, "dotplot"),
                       axis_title=x_title)
    spec["chart"] = "dotplot"
    if chosen:
        grey = context_color(current_settings())
        for row, row_name in zip(spec["rows"], names, strict=True):
            row["color"] = spec["color"] if row_name in chosen else grey
    if blocks:
        spec["rows"] = with_headings(spec["rows"], blocks)
    result = figure(title or f"{humanise(estimate)} by {str(label).replace('_', ' ')}", subtitle=subtitle,
                    caption=with_caption(caption, small, compared), size=size)
    result.draw(0, lambda box, measure, style: forest_drawing(spec, box, measure, style))
    add_reference_legend(result, legend_labels)
    return fit_height(result)


def dot_comparisons(raw: pd.DataFrame, rows: pd.DataFrame, names: list[str], blocks: list[str], columns: tuple,
                    compare: str | None, summary: str | Sequence[str] | None, digits: int | None) -> tuple:
    """With `compare`: each row's Δ and p within its block as two text columns, the columns for the forest layout and
    the caption note naming the test; otherwise the rows as they are."""
    if compare is None:
        return rows, None, None
    label, estimate, facet = columns
    blocked = blocks or [""] * len(names)
    keys = [f"{block}\x1f{name}" for block, name in zip(blocked, names, strict=True)]
    labels = raw[label].astype(str)
    within = raw[facet].astype(str) if facet else pd.Series("", index=raw.index)
    values = {key: pd.to_numeric(raw[estimate][(within == block) & (labels == name)], errors="coerce").dropna()
              .to_numpy(dtype=float) for key, block, name in zip(keys, blocked, names, strict=True)}
    found = [{"name": key, "section": block, "pairs": []} for key, block in zip(keys, blocked, strict=True)]

    def number(value: float) -> str:
        return format_number(value, digits if digits is not None else 2)
    note = section_comparisons(found, values, compare, check_summary(summary, "dotplot"), (number, number),
                               "dotplot", {key: name for key, name in zip(keys, names, strict=True)})
    texts = {"_hairline_difference": [row["pairs"][0][1] for row in found],
             "_hairline_p": [row["pairs"][1][1] for row in found]}
    headings = {word("interval", name=word("difference")): "_hairline_difference", "p": "_hairline_p"}
    return rows.assign(**texts), headings, note


def summarised(data: pd.DataFrame, label: str, estimate: str, given: tuple, facet: str | None,
               summary: str | Sequence[str]) -> tuple:
    """One row per label (per block and label with `facet`), in the order labels first appear: the centre as the
    estimate, the interval's ends and n; with the columns to read them from and the heading naming them."""
    centre, interval = check_paired(check_summary(summary, "dotplot"), "dotplot")
    if any(column is not None for column in given):
        raise ValueError("hairline: dotplot: summary computes each row's centre, interval and n from the values; "
                         "leave out low, high and n")
    check_labels(data, [label, *([facet] if facet else [])], "dotplot")
    check_numeric(data, [estimate], "dotplot")
    keys = [facet, label] if facet else [label]
    rows = []
    for key, part in data.groupby(keys, sort=False, observed=True):
        values = part[estimate].dropna().to_numpy(dtype=float)
        if not len(values):
            continue
        found = summary_values(values)
        name = str(key[-1] if isinstance(key, tuple) else key)
        if interval in ("sd", "ci") and not math.isfinite(found["sd"]):
            raise ValueError(f"hairline: dotplot: '{name}' has one value, and an {interval.upper()} needs two or "
                             f"more; min_n=2 leaves such rows out")
        ends = interval_of(found, interval) if interval else (found[centre], found[centre])
        rows.append({**({facet: key[0]} if facet else {}), label: name, estimate: found[centre],
                     SUMMARY_LOW: ends[0], SUMMARY_HIGH: ends[1], SUMMARY_N: found["n"]})
    locale = current_settings().locale
    heading = word("summary_heading", locale, centre=word(centre, locale),
                   interval=word(LEGEND_WORDS[interval], locale)) if interval else word(centre, locale)
    found = pd.DataFrame(rows, columns=[*([facet] if facet else []), label, estimate, SUMMARY_LOW, SUMMARY_HIGH,
                                        SUMMARY_N])
    return found, (SUMMARY_LOW if interval else None), (SUMMARY_HIGH if interval else None), SUMMARY_N, heading


def rows_with_min_n(data: pd.DataFrame, label: str, n: str | None, min_n: int | None) -> tuple[pd.DataFrame,
                                                                                                str | None]:
    """Rows whose `n` reaches `min_n`, and the caption note naming the others; `min_n` needs the n column."""
    if min_n is None:
        return data, None
    if n is None:
        raise ValueError("hairline: dotplot: min_n needs n=, the column holding each row's n")
    check_numeric(data, [n], "dotplot")
    kept, note = drop_small([(str(name), np.ones(int(count))) for name, count in zip(data[label], data[n],
                                                                                       strict=True)],
                            min_n, "dotplot")
    return data[data[label].astype(str).isin(dict(kept))], note


def ordered_rows(data: pd.DataFrame, label: str, estimate: str, sort: bool, order: Sequence[str] | None) -> \
        pd.DataFrame:
    """The rows in `order` when given, else largest first when sorted, else as given."""
    if order is not None:
        names = ordered_names(data[label], order, "dotplot", label)
        return data.set_index(data[label].astype(str)).loc[names].reset_index(drop=True)
    return data.sort_values(estimate, ascending=False, kind="mergesort") if sort else data


def as_percent(data: pd.DataFrame, columns: list[str | None]) -> pd.DataFrame:
    """Shares as percent: each named column × 100."""
    check_numeric(data, [column for column in columns if column], "dotplot")
    return data.assign(**{column: data[column] * 100 for column in columns if column})


def faceted_rows(data: pd.DataFrame, label: str, estimate: str, sort: bool, order: Sequence[str] | None,
                 facet: str | None) -> tuple[pd.DataFrame, list[str]]:
    """The rows, block after block when faceted (each block ordered on its own), and each row's block."""
    if facet is None:
        return ordered_rows(data, label, estimate, sort, order), []
    parts = []
    for block in dict.fromkeys(data[facet].astype(str)):
        rows = data[data[facet].astype(str) == block]
        present = set(rows[label].astype(str))
        parts.append(ordered_rows(rows, label, estimate, sort,
                                  None if order is None else [name for name in order if str(name) in present]))
    rows = pd.concat(parts)
    return rows, rows[facet].astype(str).tolist()


def with_headings(rows: list[dict], blocks: list[str]) -> list[dict]:
    """A heading row before the first row of each block."""
    found, previous = [], None
    for row, block in zip(rows, blocks, strict=True):
        if block != previous:
            found.append({"heading": block, "study": block, "cells": [], "effect_text": "", "weight_text": ""})
            previous = block
        found.append(row)
    return found
