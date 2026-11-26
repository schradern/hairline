"""The description of swimlanes for their alt text: how many intervals in how many rows, from the earliest start to the
latest end, and the longest interval as its tooltip names it. Mirrored in R's swimlanes_alt.R."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from hairline.alt_text import TIE_DIGITS, described
from hairline.charts.time_of_day import clock
from hairline.numbers import format_number, word


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
