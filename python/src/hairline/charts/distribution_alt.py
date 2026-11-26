"""The description of a distribution chart (spread, raincloud, ridgeline) for its alt text: the groups whose centre is
highest and lowest, the centre the chart draws, written as its numbers write it. Mirrored in R's
distribution_alt.R."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from hairline.alt_text import CENTRE_WORDS, described, extremes
from hairline.charts.summaries import measure_numbers, stat_pairs, summary_values
from hairline.numbers import word

# Between a facet's name and its group's ("2025 · ICU"), as the captions name a facet's rows.
FACET_PARTS = " · "


def centre_of(marks: Sequence[str]) -> str:
    """The centre the chart draws: the mean where it draws the mean and no median, else the median."""
    return "mean" if "mean" in marks and "median" not in marks else "median"


def facet_named(panels: Sequence[tuple[str | None, Sequence[tuple[str, np.ndarray]]]]) -> list[tuple[str, np.ndarray]]:
    """Every panel's groups in reading order, each named with its panel's name where there is one."""
    return [(name if panel is None else f"{panel}{FACET_PARTS}{name}", values)
            for panel, groups in panels for name, values in groups]


def distribution_description(kind: str, groups: Sequence[tuple[str, np.ndarray]], marks: Sequence[str],
                             every: np.ndarray, percent: bool, locale: str, digits: int | None = None,
                             discrete: bool = False) -> str:
    """'Interval plot. Highest median: ICU (12.5); lowest: Ward (7.0).' over the groups with values, their centre in
    the digits the chart's numbers take from `every`; groups without values are left out."""
    centre = centre_of(marks)
    numbers = measure_numbers(np.asarray(every, dtype=float), percent, digits, discrete)
    entries = [(name, float(summary_values(values, discrete)[centre]),
                stat_pairs(values, (centre,), numbers, discrete, locale)[0][1])
               for name, values in groups if len(values)]
    return described(kind, extremes(entries, locale, CENTRE_WORDS, centre=word(f"centre_{centre}", locale)), locale)
