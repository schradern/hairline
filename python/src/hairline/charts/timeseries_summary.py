"""timeseries(summary=...): the values at each x summarised, a centre line over its interval band, and the key
numbers of the panel headers, named as on every distribution chart (summaries.py)."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import pandas as pd
from matplotlib.colors import to_hex, to_rgb

from hairline.charts.summaries import (
    DASH,
    LEGEND_WORDS,
    STAT_NAMES,
    as_names,
    check_paired,
    check_summary,
    interval_of,
    measure_numbers,
    stat_label,
    stat_pairs,
    summary_values,
)
from hairline.numbers import format_percent, word
from hairline.settings import current_settings
from hairline.tokens import load_tokens

TIMESERIES_STATS = (*STAT_NAMES, "share_above")


def checked_summary(summary: str | Sequence[str] | None) -> tuple[str, str | None] | None:
    """The centre and interval drawn over time, or None for the raw values under a rolling mean."""
    return None if summary is None else check_paired(check_summary(summary, "timeseries"), "timeseries")


def summary_series(rows: pd.DataFrame, x: str, y: str, centre: str, interval: str | None) -> pd.DataFrame:
    """Per x, in order: the centre and the interval's ends (NaN where an SD or CI has one value only)."""
    found = []
    for position, part in rows.dropna(subset=[y]).groupby(x, sort=True):
        values = summary_values(part[y].to_numpy(dtype=float))
        low, high = interval_of(values, interval) if interval else (math.nan, math.nan)
        found.append({x: position, "centre": values[centre], "low": low, "high": high})
    return pd.DataFrame(found, columns=[x, "centre", "low", "high"])


def draw_summary_series(ax, rows: pd.DataFrame, x: str, y: str, color: str, marks: tuple[str, str | None]) -> None:
    """The interval as a band in the series' colour, the centre as its line over it."""
    lines, base = load_tokens()["lines"], current_settings().base_size
    series = summary_series(rows, x, y, *marks)
    if marks[1]:
        ax.fill_between(series[x], series["low"], series["high"], color=color, alpha=lines["band_opacity"],
                        linewidth=0, label="_nolegend_")
    ax.plot(series[x], series["centre"], color=color, linewidth=lines["data"] * base)


def summary_legend_items(marks: tuple[str, str | None]) -> list[tuple[str, str, str]]:
    """The centre's line and the interval's band, in ink and in ink over the surface at the band's opacity."""
    neutral, opacity = current_settings().neutral, load_tokens()["lines"]["band_opacity"]
    centre, interval = marks
    items = [("line", neutral["ink"], word(centre))]
    if interval:
        ink, surface = np.array(to_rgb(neutral["ink"])), np.array(to_rgb(neutral["surface"]))
        items.append(("band", to_hex(surface + (ink - surface) * opacity), word(LEGEND_WORDS[interval])))
    return items


def panel_stats(values: pd.Series, stats: Sequence[str], percent: bool, threshold: float | None,
                share_label: str) -> list[tuple[str, str]]:
    """A panel's key numbers: any shared measure (stats=) and the share at or above `threshold`."""
    names = as_names(stats, "timeseries", "stats", TIMESERIES_STATS)
    clean = values.dropna().to_numpy(dtype=float)
    measures = [name for name in names if name != "share_above"]
    found = dict(zip(measures, stat_pairs(clean, measures, measure_numbers(clean, percent, None)), strict=True)) \
        if len(clean) else {name: [stat_label(name), DASH] for name in measures}
    pairs = []
    for name in names:
        if name == "share_above":
            if threshold is None:
                raise ValueError("hairline: stats 'share_above' needs threshold=")
            pairs.append((share_label, format_percent(float((clean >= threshold).mean()), 0) if len(clean) else DASH))
        else:
            pairs.append(tuple(found[name]))
    return pairs
