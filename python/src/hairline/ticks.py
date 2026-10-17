"""Tick positions shared with the R package: 3 to 6 'nice' breaks covering the data range."""

from __future__ import annotations

import datetime as dt
import math

from hairline.tokens import load_tokens

EPSILON = 1e-9


def padded_range(low: float, high: float) -> tuple[float, float]:
    if high > low:
        return low, high
    pad = abs(low) * 0.25 if low != 0 else 1.0
    return low - pad, high + pad


def variants(low: float, high: float, step: float, rules: dict, wants_zero: bool) -> list[tuple[float, float]]:
    """Break ranges the data passes by at most 10 % below / 20 % above their extent, never on the side facing zero
    when zero belongs on the axis."""
    start = math.floor(low / step + EPSILON) * step
    end = math.ceil(high / step - EPSILON) * step
    options = []
    for first in (start, start + step):
        for last in (end, end - step):
            extent = last - first
            faces_zero = wants_zero and ((low >= 0 and first > low + 1e-12) or (high <= 0 and last < high - 1e-12))
            if extent > 0 and not faces_zero and first - low <= rules["overshoot_low"] * extent + 1e-12 and \
                    high - last <= rules["overshoot_high"] * extent + 1e-12:
                options.append((first, last))
    return options


def near_zero(low: float, high: float) -> bool:
    """Zero belongs on the axis when the data spans it or starts within the lower half of its magnitude."""
    return low <= 0 <= high or 0 < low <= 0.5 * high or 0.5 * low <= high < 0


def misfit(low: float, high: float, start: float, end: float, wants_zero: bool) -> float:
    """The larger of the empty share of the axis and the share by which data passes the outer breaks."""
    extent = end - start
    floor = min(low, 0.0) if wants_zero and low > 0 else low
    ceiling = max(high, 0.0) if wants_zero and high < 0 else high
    empty = max(0.0, floor - start) + max(0.0, end - ceiling)
    overshoot = max(0.0, start - low) + max(0.0, high - end)
    return round(max(empty, overshoot) / extent, 9)


def nice_breaks(low: float, high: float, target: int = 5) -> list[float]:
    """Return 3 to 6 round values; data may pass the first break by 10 % and the last by 20 % of the axis."""
    if low > high:
        raise ValueError(f"hairline: nice_breaks got low {low:g} is above high {high:g}; pass the range in order")
    rules = load_tokens()["ticks"]
    low, high = padded_range(low, high)
    magnitude = math.floor(math.log10(high - low))
    wants_zero = near_zero(low, high)
    best = None
    for exponent in range(magnitude - 1, magnitude + 2):
        for multiplier in rules["multipliers"]:
            step = multiplier * 10.0 ** exponent
            for start, end in variants(low, high, step, rules, wants_zero):
                count = round((end - start) / step) + 1
                if not rules["min"] <= count <= rules["max"]:
                    continue
                misses_zero = wants_zero and not start <= 0 <= end
                key = (abs(count - target), misses_zero, misfit(low, high, start, end, wants_zero), end - start,
                       -step)
                if best is None or key < best[0]:
                    best = (key, start, step, count)
    if best is None:
        raise ValueError(f"hairline: no tick spacing found for range {low:g} to {high:g}")
    _, start, step, count = best
    return [float(f"{start + index * step:.10g}") for index in range(count)]


def axis_limits(low: float, high: float, breaks: list[float]) -> tuple[float, float]:
    """Axis range: the breaks, widened to any data that passes them."""
    return min(low, breaks[0]), max(high, breaks[-1])


def month_starts(low: dt.date, high: dt.date, step: int) -> list[dt.date]:
    """First days of months in [low, high] whose month is aligned to January in steps of `step`."""
    days, year, month = [], low.year, low.month
    while (year, month) <= (high.year, high.month):
        day = dt.date(year, month, 1)
        if low <= day <= high and (month - 1) % step == 0:
            days.append(day)
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return days


def month_breaks(low: dt.date, high: dt.date, target: int = 5) -> list[dt.date]:
    """Month ticks: the January-aligned step with 3 to 7 ticks closest to `target` (ties: larger step)."""
    best = None
    for step in load_tokens()["ticks"]["month_steps"]:
        days = month_starts(low, high, step)
        if 3 <= len(days) <= 7 and (best is None or abs(len(days) - target) <= abs(len(best) - target)):
            best = days
    return best if best is not None else month_starts(low, high, 1)


def month_label(day: dt.date, locale: str) -> str:
    """'2025' at January, otherwise the month's short name in the locale."""
    return str(day.year) if day.month == 1 else load_tokens()["locales"][locale]["months"][day.month - 1]
