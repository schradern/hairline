"""The description of Kaplan–Meier curves for their alt text: each group's median as the panel header writes it, or
where the curve stays above half, the share still without the event at its last time; and the log-rank p where the
chart shows one, labelled as the panel header labels it. Mirrored in R's kaplan_meier_alt.R."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from hairline.alt_text import described
from hairline.numbers import auto_digits, format_number, format_percent, word
from hairline.stats.survival import km_median, median_digits


def median_part(table: pd.DataFrame, digits: int, time_digits: int, locale: str) -> str:
    """A curve's median, or 'not reached (62% at 24)' with the survival at its last time."""
    median = km_median(table)
    if median is not None:
        return format_number(median, digits, locale)
    last = table.iloc[-1]
    return word("km_not_reached", locale, share=format_percent(float(last["survival"]), 0, locale),
                time=format_number(float(last["time"]), time_digits, locale))


def kaplan_meier_description(estimates: Sequence[tuple[str, pd.DataFrame]], grouped: bool,
                             stats: Sequence[tuple[str, str]], locale: str) -> str:
    """'Kaplan–Meier curve. Median: ICU 9.1; Ward not reached (62% at 24). Log-rank: p = 0.003.' Groups are named
    only where the chart has several; the p is the log-rank one among the panel header's numbers, with its label."""
    tables = [table for _, table in estimates]
    digits = median_digits(tables)
    times = np.concatenate([table["time"].to_numpy(dtype=float) for table in tables])
    time_digits = auto_digits(times[times > 0])
    medians = "; ".join(f"{name} {median_part(table, digits, time_digits, locale)}" if grouped
                        else median_part(table, digits, time_digits, locale) for name, table in estimates)
    tests = [(str(label), str(value)) for label, value in stats if str(label).lower().startswith("log-rank")]
    findings = [word("km_medians", locale, medians=medians),
                *[word("km_test", locale, label=label, value=value) for label, value in tests[:1]]]
    return described("kind_kaplan_meier", " ".join(findings), locale)
