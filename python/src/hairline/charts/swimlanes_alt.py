"""The descriptions of the time-of-day charts for their alt text: swimlanes' intervals and rows, from the earliest start
to the latest end, and the longest interval as its tooltip names it; lanes' rows and their highest cell as its tooltip
names it. Mirrored in R's swimlanes_alt.R."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from hairline.alt_text import TIE_DIGITS, described
from hairline.charts.time_of_day import clock, hour_span
from hairline.numbers import format_number, format_percent, word


def counted(count: int, one: str, many: str, locale: str) -> str:
    """'1 interval' or '12 intervals'."""
    return word(one, locale) if count == 1 else word(many, locale, n=format_number(count, 0, locale))


def swimlanes_description(names: Sequence[str], starts: np.ndarray, ends: np.ndarray, rows: int,
                          locale: str) -> str:
    """'Swimlane chart. 12 intervals in 5 rows, from 07:15 to 18:30. Longest: Hip · Theatre 2, 08:00–12:30.'; each
    interval named as its tooltip names it, the first of equally long ones, and no longest for a single one."""
    span = word("swimlanes_span", locale, intervals=counted(len(names), "intervals_one", "intervals_many", locale),
                rows=counted(rows, "rows_one", "rows_many", locale), start=clock(float(np.min(starts))),
                end=clock(float(np.max(ends))))
    if len(names) == 1:
        return described("kind_swimlanes", span, locale)
    lengths = np.round(ends - starts, TIE_DIGITS)
    index = int(np.flatnonzero(lengths == lengths.max())[0])
    longest = word("swimlanes_longest", locale, name=names[index], start=clock(float(starts[index])),
                   end=clock(float(ends[index])))
    return described("kind_swimlanes", f"{span} {longest}", locale)


def lanes_description(matrix: dict[str, np.ndarray], bin_minutes: int, share: bool, locale: str) -> str:
    """'Lane chart. 6 rows; highest at Bed 3, 10:00–10:30 (95%).' over the cells as their tooltips write them, the
    first of equally high ones reading row by row; a share of days in percent, else the mean count."""
    rows = list(matrix)
    every = np.round(np.concatenate([matrix[name] for name in rows]), TIE_DIGITS)
    found = int(np.flatnonzero(every == every.max())[0])
    bins = len(matrix[rows[0]])
    name, amount = rows[found // bins], float(matrix[rows[found // bins]][found % bins])
    low, high = hour_span(found % bins, bin_minutes)
    value = format_percent(amount, 0, locale) if share else format_number(amount, 1, locale)
    peak = word("lanes_peak", locale, rows=counted(len(rows), "rows_one", "rows_many", locale), name=name,
                start=clock(low), end=clock(high), value=value)
    return described("kind_lanes", peak, locale)
