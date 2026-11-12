"""The raincloud's numbers under the groups: rows of measures (stats=) and of comparisons (compare=), each value
under its group, as the n row."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from hairline.charts.comparisons import check_compare, compare_caption, compare_method, comparison_pairs
from hairline.charts.summaries import SUMMARY_NAMES, as_names, measure_numbers, stat_pairs
from hairline.charts.tips import pairs_tip, tip_measures


def check_raincloud_stats(stats: str | Sequence[str], facet: str | None) -> tuple[str, ...]:
    """The measures written under the groups; n has its own row (show_n), and panels have no row under them."""
    stats = as_names(stats, "raincloud", "stats", SUMMARY_NAMES)
    if stats and facet:
        raise ValueError("hairline: raincloud: stats writes a row of numbers under the groups, which facet panels do "
                         "not have; use spread(facet=...), which lists the numbers beside each block's rows")
    return stats


def stat_rows(groups: Sequence[pd.Series], stats: Sequence[str], percent: bool, locale: str) -> list[tuple]:
    """One table row per measure, its label on the left, each group's number under the group."""
    if not stats:
        return []
    values = [values.to_numpy(dtype=float) for values in groups]
    numbers = measure_numbers(np.concatenate(values), percent, None)
    found = [stat_pairs(group, stats, numbers, locale=locale) for group in values]
    return [(found[0][row][0], None, [(float(position), pairs[row][1]) for position, pairs in enumerate(found)])
            for row in range(len(stats))]


def compare_rows(groups: list[tuple[str, np.ndarray]], compare: str | None, facet: str | None,
                 marks: Sequence[str], percent: bool, locale: str) -> tuple[list[tuple], str | None, dict]:
    """The Δ and p rows under the groups, each against the reference or the group to its left, the caption note
    naming the test, and each group's Δ and p pairs (for its tooltip); none without compare."""
    compare = check_compare(compare, [name for name, _ in groups], "raincloud")
    if compare is None:
        return [], None, {}
    if facet:
        raise ValueError("hairline: raincloud: compare writes rows of numbers under the groups, which facet panels "
                         "do not have; use spread(facet=..., compare=...), which compares within each block")
    numbers = measure_numbers(np.concatenate([values for _, values in groups]), percent, None)
    method = compare_method(marks)
    found = comparison_pairs(groups, compare, method, numbers, locale)
    rows = [(found[groups[0][0]][row][0], None, [(float(position), found[name][row][1]) for position, (name, _) in
                                                  enumerate(groups)]) for row in range(2)]
    return rows, compare_caption(compare, method, len(groups) - 1, locale), found


def group_tips(groups: Sequence[tuple[str, np.ndarray]], every: np.ndarray, marks: Sequence[str],
               stats: Sequence[str], compared: dict, percent: bool, locale: str) -> dict[str, str]:
    """Each group's summary tooltip: the measures it draws and writes, its n, and its Δ and p with compare, in the
    numbers' own digits (the measures of all groups set them, as for the rows under the groups)."""
    numbers = measure_numbers(every, percent, None)
    measures = tip_measures(marks, stats)
    return {name: pairs_tip(name, stat_pairs(values, measures, numbers, locale=locale) + compared.get(name, []))
            for name, values in groups if len(values)}
