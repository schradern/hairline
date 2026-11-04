"""Counts of people (or places) over the time of day as steps on whole-number levels: how often exactly 1, 2, 3 …
were needed (one shaded row per count, as lanes shade their cells), the typical day (median, dashed) and the count
that is enough on most days (the decision line, bold). Quantiles stay on the data's levels: people only come
whole."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd
from matplotlib.collections import PolyCollection

from hairline import entities
from hairline.charts.common import check_columns, check_numeric, humanise
from hairline.charts.time_of_day import (
    MINUTES,
    add_caption,
    add_legend,
    as_times,
    binned,
    calendar,
    check_bin,
    check_steps,
    clock,
    day_count,
    day_origin,
    hour_span,
    interval_rows,
    kept_rows,
    minute_counts,
    step_colors,
    step_index,
    target_panels,
)
from hairline.charts.timeseries import groups_of
from hairline.figure import HairlineFigure, figure
from hairline.marks import lone_color
from hairline.numbers import format_number, format_percent, word
from hairline.settings import current_settings
from hairline.stats.density import level_quantiles
from hairline.tokens import load_tokens

TYPICAL = ("median", None)


def sample_peaks(rows: pd.DataFrame, time: str, count: str, origin: pd.Timestamp, total: int,
                 bin_minutes: int) -> np.ndarray:
    """Counts sampled at times: each (day, bin)'s peak; a bin without a sample counts as 0, nobody needed."""
    times = as_times(rows[time], time, "levels")
    minutes = np.floor((times - origin).dt.total_seconds().to_numpy() / 60).astype(int)
    values = np.zeros(total * MINUTES)
    np.maximum.at(values, np.clip(minutes, 0, total * MINUTES - 1), rows[count].to_numpy(dtype=float))
    return binned(values, bin_minutes, "peak")


def check_quantile(quantile: object) -> float:
    if isinstance(quantile, bool) or not isinstance(quantile, float | int) or not 0 < quantile < 1:
        raise ValueError(f"hairline: levels: quantile must lie between 0 and 1 (0.9: enough on 9 of 10 days); got "
                         f"{quantile!r}")
    return float(quantile)


def peaks_per_group(data: pd.DataFrame, time: str, count: str | None, end: str | None, by: str | None,
                    bin_minutes: int, days: object) -> tuple[list[tuple[str, np.ndarray]], str]:
    """Per group the peak per kept day and bin: from intervals (people or patients present at once) or from counts
    sampled at times."""
    if end is not None:
        starts, ends = interval_rows(data, time, end, "levels")
        origin, total = day_origin(starts), day_count(starts, ends)
    else:
        check_numeric(data, [count], "levels")
        times = as_times(data[time], time, "levels")
        origin, total = times.min().normalize(), int((times.max().normalize() - times.min().normalize()).days) + 1
    kept, label = calendar(origin, origin + np.timedelta64(total - 1, "D"), days, "levels")
    chosen, found = kept_rows(kept, origin), []
    for name, rows in groups_of(data, by, None, "levels"):
        if end is not None:
            start_times, end_times = interval_rows(rows, time, end, "levels")
            peaks = binned(minute_counts(start_times, end_times, origin, total), bin_minutes, "peak")
        else:
            peaks = sample_peaks(rows, time, count, origin, total, bin_minutes)
        found.append((name, peaks[chosen].astype(float)))
    return found, label


def level_lines(peaks: np.ndarray, quantile: float, typical: str | None) -> tuple[np.ndarray, np.ndarray | None]:
    """The decision line (the `quantile` of each bin's daily peaks) and the typical one (their median), both on the
    data's levels."""
    decision = np.array([level_quantiles(peaks[:, column], [quantile])[0] for column in range(peaks.shape[1])])
    middle = None if typical is None else np.array([level_quantiles(peaks[:, column], [0.5])[0]
                                                    for column in range(peaks.shape[1])])
    return decision, middle


def step_xy(values: np.ndarray, bins: np.ndarray, bin_minutes: int) -> tuple[list[float], list[float]]:
    """A steps-post line over the bins shown, ending at the last bin's end."""
    xs = [hour_span(int(index), bin_minutes)[0] for index in bins] + [hour_span(int(bins[-1]), bin_minutes)[1]]
    ys = [float(values[index]) for index in bins]
    return xs, ys + ys[-1:]


def draw_shading(result: HairlineFigure, index: int, name: str, peaks: np.ndarray, bins: np.ndarray, color: str,
                 steps: list[float], bin_minutes: int) -> None:
    """One shaded row per count from 1 up: each bin's share of days that needed exactly that many, binned as the
    key shows."""
    ramp, top = step_colors(color, len(steps)), int(peaks.max())
    polygons, faces = [], []
    half = load_tokens()["lanes"]["cell"] / 2
    for level in range(1, top + 1):
        for bin_index in bins:
            share = float((peaks[:, bin_index] == level).mean())
            if share <= 0:
                continue
            low, high = hour_span(int(bin_index), bin_minutes)
            polygons.append([(low, level - half), (high, level - half), (high, level + half), (low, level + half)])
            faces.append(ramp[step_index(share, steps)])
            result.hover(index, f"{name or 'Count'} {level}", color, (low, level - half, high, level + half),
                         f"{name + ': ' if name else ''}{format_number(level, 0)}, {clock(low)}–{clock(high)}: "
                         f"{format_percent(share, 0)}")
    result.axes[index].add_collection(PolyCollection(polygons, facecolors=faces, edgecolors="none", linewidths=0,
                                                     zorder=1), autolim=True)


def levels(data: pd.DataFrame, time: str, count: str | None = None, *, end: str | None = None,
           by: str | None = None, bin: int | None = None, quantile: float | None = None,
           typical: str | None = "median", shade: bool = True, days: object = None,
           order: Sequence[str] | None = None, steps: Sequence[float] | None = None,
           hours: tuple[float, float] | None = None, spans: Mapping[str, tuple[float, float]] | None = None,
           colors: Mapping[str, str] | None = None, dimension: str | None = None, key_title: str | None = None,
           title: str | None = None, subtitle: str | None = None, caption: str | None = None, size: str = "double",
           into: HairlineFigure | None = None, panel: int = 0) -> HairlineFigure:
    """Whole counts over the time of day, one panel per group of `by` (doctors, nurses): from intervals (`time` the
    start, `end` the end: the people present at once) or from counts sampled at times (`count`). Per `bin`, each
    day's peak; then the share of days that needed exactly 1, 2, 3 … (`shade`, binned at `steps`), the typical day
    (the median, dashed; `typical=None` leaves it out) and the count that is enough on `quantile` of the days (0.9
    by default; bold). Both lines are steps on the data's levels (R's quantile type 1), and the panel header gives
    their highest values ("Up to 3 · Typical 2"). `days`, `hours`, `spans`, `into` and `panel` work as in
    `lanes()`."""
    check_columns(data, [time, count, end, by])
    if (count is None) == (end is None):
        raise ValueError("hairline: levels: give count= (counts at times) or end= (intervals), not both")
    if typical not in TYPICAL:
        raise ValueError(f"hairline: levels: typical {typical!r} must be 'median' or None")
    quantile = check_quantile(load_tokens()["levels"]["quantile"] if quantile is None else quantile)
    bin_minutes, steps = check_bin(bin or load_tokens()["lanes"]["bin"], "levels"), check_steps(steps, "levels")
    groups, day_label = peaks_per_group(data, time, count, end, by, bin_minutes, days)
    if order is not None:
        named = dict(groups)
        groups = [(str(name), named[str(name)]) for name in order]
    locale = current_settings().locale
    subtitle_text = " · ".join(part for part in (subtitle, day_label) if part) or None
    rules = load_tokens()["levels"]
    tallest = max(int(peaks.max()) for _, peaks in groups) + 1

    def make() -> HairlineFigure:
        made = figure(title or f"{humanise(count or 'people')} over the day", subtitle=subtitle_text,
                      caption=caption, size=size, height_mm=40, panels=len(groups), layout="rows", sharey=False)
        made.min_plot = len(groups) * max(tallest, rules["min_rows"]) * rules["row_pitch"]
        return made
    result, indexes = target_panels(into, panel, len(groups), make)
    names = [name for name, _ in groups]
    with entities.chart(names if by else [], colors, dimension) as palette:
        colours = {name: palette.get(name, lone_color()) for name in names}
    base, neutral = result.settings.base_size, result.settings.neutral
    occupied = np.flatnonzero(np.any([peaks.max(axis=0) > 0 for _, peaks in groups], axis=0))
    if not len(occupied):
        raise ValueError("hairline: levels: every count is 0 on the days kept; nothing to draw")
    shown = np.arange(occupied.min(), occupied.max() + 1)
    share = format_percent(quantile, 0, locale)
    for index, (name, peaks) in zip(indexes, groups, strict=True):
        ax = result.axes[index]
        if shade:
            draw_shading(result, index, name, peaks, shown, colours[name], steps, bin_minutes)
        decision, middle = level_lines(peaks, quantile, typical)
        if middle is not None:
            xs, ys = step_xy(middle, shown, bin_minutes)
            ax.plot(xs, ys, drawstyle="steps-post", color=neutral["muted"], label="_nolegend_",
                    linewidth=load_tokens()["reference"]["width"] * base * 1.5,
                    linestyle=(0, tuple(rules["typical_dash"])), zorder=3, gid="hairline-static")
        xs, ys = step_xy(decision, shown, bin_minutes)
        ax.plot(xs, ys, drawstyle="steps-post", color=neutral["ink"], linewidth=rules["decision_width"] * base,
                zorder=4, label=f"{name}: {word('decision', locale, share=share)}" if name else
                word("decision", locale, share=share), solid_joinstyle="miter")
        ax.set_ylim(-0.5, max(int(peaks.max()), 1) + 0.5)
        result.integer_axis(index, "y")
        result.time_axis(index, hours, spans)
        stats = [(word("up_to", locale), format_number(decision.max(), 0, locale))]
        if middle is not None:
            stats.append((word("typical", locale), format_number(middle.max(), 0, locale)))
        result.panel_header(index, name or humanise(count or word("people", locale)), stats=stats,
                            key=word("up_to", locale))
    items = [("line", neutral["ink"], word("decision", locale, share=share))]
    if typical:
        items.append(("dash", neutral["muted"], word("typical_line", locale)))
    add_legend(result, items)
    if shade:
        key = step_colors(next(iter(colours.values())), len(steps)) if len(colours) == 1 else \
            step_colors(None, len(steps))
        result.legend_ramp(key, steps, key_title or word("share_of_days", locale))
    add_caption(result, word("levels_note", locale), f"{day_label}." if into is not None and day_label else None)
    return result
