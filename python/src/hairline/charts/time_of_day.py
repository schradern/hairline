"""The time of day, shared by lanes(), levels() and swimlanes(): clock hours from dates, the calendar filter, bins
over the day, intervals per day and the first-free assignment of tasks to people; then the drawing helpers the
three share (panels to draw in, the legend row, binned colours, row blocks)."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import pandas as pd

from hairline.charts.timeseries import iso_datetimes
from hairline.numbers import format_number, word

MINUTES = 1440
DAY_NAMES = ("weekdays", "weekends")


def as_times(values: pd.Series, column: str, chart: str) -> pd.Series:
    """Dates and times (or ISO text) as timestamps; anything else is refused with the column named."""
    if pd.api.types.is_datetime64_any_dtype(values):
        return values
    parsed = iso_datetimes(values)
    if parsed.notna().sum() != values.notna().sum():
        raise ValueError(f"hairline: {chart}: '{column}' needs dates with times (2026-03-02 07:15); "
                         f"got {values.dropna().iloc[0]!r}")
    return parsed


def clock_hours(values: pd.Series, column: str, chart: str) -> np.ndarray:
    """Hours since midnight: numbers as they are (7.25), 'HH:MM' text, or the time of a date (07:15 is 7.25)."""
    if pd.api.types.is_numeric_dtype(values) and not pd.api.types.is_bool_dtype(values):
        return values.to_numpy(dtype=float)
    text = values.astype(str)
    if text.str.fullmatch(r"\d{1,2}:\d{2}").all():
        parts = text.str.split(":", expand=True).astype(int)
        return (parts[0] + parts[1] / 60).to_numpy(dtype=float)
    times = as_times(values, column, chart)
    return ((times - times.dt.normalize()).dt.total_seconds() / 3600).to_numpy(dtype=float)


def check_bin(bin_minutes: object, chart: str) -> int:
    if isinstance(bin_minutes, bool) or not isinstance(bin_minutes, int) or bin_minutes < 1 or MINUTES % bin_minutes:
        raise ValueError(f"hairline: {chart}: bin must be a whole number of minutes that divides a day (5, 10, 15, "
                         f"30, 60); got {bin_minutes!r}")
    return bin_minutes


def calendar(first: pd.Timestamp, last: pd.Timestamp, days: object, chart: str) -> tuple[pd.DatetimeIndex, str]:
    """The days from the first to the last in the data, kept by the calendar filter: None (all), "weekdays",
    "weekends", or a list of dates; and its name with its n for the subtitle ("Weekdays, 128 days")."""
    every = pd.date_range(first.normalize(), last.normalize(), freq="D")
    if days is None:
        kept, name = every, word("all_days")
    elif isinstance(days, str):
        if days not in DAY_NAMES:
            raise ValueError(f"hairline: {chart}: days {days!r} must be 'weekdays', 'weekends' or a list of dates")
        kept = every[every.dayofweek < 5] if days == "weekdays" else every[every.dayofweek >= 5]
        name = word(days)
    else:
        kept = pd.DatetimeIndex(pd.to_datetime(list(days))).normalize()
        outside = kept[~kept.isin(every)]
        if len(outside):
            raise ValueError(f"hairline: {chart}: days names {outside[0].date()}, which the data does not cover "
                             f"({every[0].date()} to {every[-1].date()})")
        name = None
    if not len(kept):
        raise ValueError(f"hairline: {chart}: the calendar filter {days!r} keeps no day of the data")
    count = word("days", n=format_number(len(kept), 0))
    return kept, f"{name}, {count}" if name else count


def minute_counts(starts: pd.Series, ends: pd.Series, origin: pd.Timestamp, total_days: int) -> np.ndarray:
    """Intervals at the same time, minute by minute from `origin` over `total_days` days (an interval covers the
    minutes it touches; one that crosses midnight runs on into the next day)."""
    begin = np.floor((starts - origin).dt.total_seconds().to_numpy() / 60).astype(int)
    finish = np.ceil((ends - origin).dt.total_seconds().to_numpy() / 60).astype(int)
    total = total_days * MINUTES
    delta = np.zeros(total + 1, dtype=int)
    begin, finish = np.clip(begin, 0, total), np.clip(np.maximum(finish, begin + 1), 0, total)
    np.add.at(delta, begin, 1)
    np.add.at(delta, finish, -1)
    return np.cumsum(delta)[:total]


def binned(minutes: np.ndarray, bin_minutes: int, how: str) -> np.ndarray:
    """Minute values as (day, bin) of the day: the peak in each bin, or whether any minute is above zero."""
    shaped = minutes.reshape(-1, MINUTES // bin_minutes, bin_minutes)
    return shaped.max(axis=2) if how == "peak" else (shaped > 0).any(axis=2)


def interval_rows(data: pd.DataFrame, start: str, end: str, chart: str) -> tuple[pd.Series, pd.Series]:
    starts, ends = as_times(data[start], start, chart), as_times(data[end], end, chart)
    backwards = np.flatnonzero((ends < starts).to_numpy())
    if len(backwards):
        raise ValueError(f"hairline: {chart}: row {backwards[0] + 1} ends before it starts ({starts.iloc[backwards[0]]}"
                         f" to {ends.iloc[backwards[0]]})")
    return starts, ends


def day_origin(starts: pd.Series) -> pd.Timestamp:
    return starts.min().normalize()


def day_count(starts: pd.Series, ends: pd.Series) -> int:
    return int((ends.max().normalize() - day_origin(starts)).days) + 1


def kept_rows(days: pd.DatetimeIndex, origin: pd.Timestamp) -> np.ndarray:
    return ((days - origin).days).to_numpy()


# Float noise a data limit may carry (a span from 7 reads 6.999999999999998 once the axes are placed).
HOUR_NOISE = 1e-9


def hour_window(lows: Sequence[float], highs: Sequence[float], margin: float) -> tuple[float, float]:
    """The hours with data plus a margin, on whole hours: 06 to 22 rather than a night of nothing."""
    low, high = min(lows), max(highs)
    return max(0.0, math.floor(low + HOUR_NOISE) - margin), min(48.0, math.ceil(high - HOUR_NOISE) + margin)


def first_free(starts: Sequence[float], ends: Sequence[float]) -> list[int]:
    """Each task to the first person free at its start, people numbered from 1 in the order they are needed;
    tasks in order of start (then end), so the result is the least number of people the tasks need."""
    order = sorted(range(len(starts)), key=lambda index: (starts[index], ends[index], index))
    free_at: list[float] = []
    people = [0] * len(starts)
    for index in order:
        person = next((number for number, until in enumerate(free_at) if until <= starts[index]), None)
        if person is None:
            free_at.append(ends[index])
            person = len(free_at) - 1
        else:
            free_at[person] = ends[index]
        people[index] = person + 1
    return people


# Drawing helpers shared by the three charts.

def target_panels(into, panel: int, count: int, make) -> tuple[object, list[int]]:
    """The figure and panel indexes to draw in: `count` panels from `panel` of the figure given (a composition of
    rows on one time axis), else a new figure from `make()`."""
    if into is None:
        return make(), list(range(count))
    from hairline.figure import HairlineFigure
    if not isinstance(into, HairlineFigure):
        raise ValueError(f"hairline: into must be a figure from hl.figure(); got {type(into).__name__}")
    indexes = list(range(panel, panel + count))
    if indexes[-1] >= len(into.axes):
        raise ValueError(f"hairline: into: {count} panel(s) from panel {panel} need {indexes[-1] + 1} panels; the "
                         f"figure has {len(into.axes)}")
    return into, indexes


def add_legend(figure, items: Sequence[tuple[str, str, str]]) -> None:
    """Add items to the figure's explicit legend row, each label once (charts drawn into one figure share it)."""
    from hairline.layout.legend import validate_items
    current = list(figure.legend_items or []) + list(figure.extra_legend_items)
    figure.extra_legend_items = []
    labels = [item.label for item in current]
    figure.legend_items = current + [item for item in validate_items(items) if item.label not in labels]
    figure.collect_legend = False


def add_caption(figure, *notes: str | None) -> None:
    from hairline.charts.common import with_caption
    figure.caption = with_caption(figure.caption, *[note for note in notes if note and note not in
                                                     (figure.caption or "")])


def step_colors(base: str | None, count: int) -> list[str]:
    """`count` colours of one hue from light to dark (the ramp of a group's colour, or greys), its near-white
    first step left out so the lightest bin still reads on the surface."""
    from hairline.color.ramps import sequential_ramp
    from hairline.color.space import hex_to_oklch
    from hairline.palettes import interpolate
    hue = None if base is None else hex_to_oklch(base)[2]
    return interpolate(sequential_ramp(hue), count + 1)[1:]


def step_index(value: float, steps: Sequence[float]) -> int:
    """The bin of a value: the first step it does not exceed (the last for anything above)."""
    return next((index for index, step in enumerate(steps) if value <= step + 1e-12), len(steps) - 1)


def check_steps(steps: Sequence[float] | None, chart: str) -> list[float]:
    from hairline.tokens import load_tokens
    found = [float(step) for step in (steps if steps is not None else load_tokens()["legend_ramp"]["steps"])]
    if not found or any(not 0 < step <= 1 for step in found) or found != sorted(set(found)):
        raise ValueError(f"hairline: {chart}: steps must rise within (0, 1], such as (0.25, 0.5, 0.75, 1); "
                         f"got {steps!r}")
    return found


def short_label(name: str, block: str) -> str:
    """A row's label inside its block: 'Theatre 2' in block 'Theatre' reads '2'; other names stay whole."""
    if block and name.startswith(block) and name[len(block):].strip():
        return name[len(block):].strip()
    return name


def row_layout(rows: Sequence[str], groups: Sequence[str] | None, palette: dict[str, str],
               lone: str) -> tuple[list[tuple[str, str, list[str]]], dict[str, float], dict[str, str]]:
    """Blocks for row_blocks(), each row's y (top row highest) and each row's colour (its group's)."""
    blocks: list[tuple[str, str, list[str]]] = []
    colours: dict[str, str] = {}
    for name, group in zip(rows, groups or [""] * len(rows), strict=True):
        colours[name] = palette.get(group, lone)
        if blocks and blocks[-1][0] == group:
            blocks[-1][2].append(short_label(name, group))
        else:
            blocks.append((group, colours[name], [short_label(name, group)]))
    ys = {name: float(len(rows) - 1 - index) for index, name in enumerate(rows)}
    return blocks, ys, colours


def separators(ax, blocks: Sequence[tuple[str, str, list[str]]], width: float, color: str) -> None:
    """A hairline between row blocks."""
    from hairline.marks import FIXED_ID
    position = sum(len(rows) for _, _, rows in blocks) - 0.5
    for _, _, rows in blocks[:-1]:
        position -= len(rows)
        ax.axhline(position, color=color, linewidth=width, zorder=3, gid=FIXED_ID, label="_nolegend_")


def hour_span(bin_index: int, bin_minutes: int) -> tuple[float, float]:
    start = bin_index * bin_minutes / 60
    return start, start + bin_minutes / 60


def clock(hours: float) -> str:
    minutes = int(round(hours * 60)) % MINUTES
    return f"{minutes // 60:02d}:{minutes % 60:02d}"
