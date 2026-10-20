"""Kaplan–Meier estimate with Greenwood variance and a 95 % band on the log scale, as survival::survfit's default."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import pandas as pd

Z_95 = 1.959963984540054


def check_inputs(time: np.ndarray, event: np.ndarray) -> None:
    if len(time) == 0 or len(time) != len(event):
        raise ValueError(f"hairline: Kaplan–Meier needs as many times as events and at least one; got {len(time)} "
                         f"times and {len(event)} events")
    missing = np.flatnonzero(np.isnan(time) | np.isnan(event))
    if len(missing):
        raise ValueError(f"hairline: Kaplan–Meier time and event must not be missing; row {missing[0] + 1} has "
                         f"time {time[missing[0]]:g} and event {event[missing[0]]:g}")
    unknown = sorted(set(np.unique(event)) - {0, 1})
    if unknown:
        raise ValueError(f"hairline: Kaplan–Meier event values must be 0 or 1; found {unknown[0]:g}")
    if np.any(time < 0):
        raise ValueError(f"hairline: Kaplan–Meier time {time[time < 0][0]:g} is negative; times count from 0")


def band(survival: float, variance: float) -> tuple[float, float]:
    if survival <= 0 or math.isinf(variance):
        return math.nan, math.nan
    spread = Z_95 * math.sqrt(variance)
    return survival * math.exp(-spread), min(1.0, survival * math.exp(spread))


def km_estimate(time: Sequence[float], event: Sequence[int]) -> pd.DataFrame:
    """One row per distinct time: at risk, events, censored, survival and its 95 % band."""
    time, event = np.asarray(time, dtype=float), np.asarray(event, dtype=float)
    check_inputs(time, event)
    moments, position = np.unique(time, return_inverse=True)
    events_at = np.bincount(position, weights=event, minlength=len(moments)).astype(int)
    leaving = np.bincount(position, minlength=len(moments))
    at_risk_at_moment = len(time) - np.concatenate([[0], np.cumsum(leaving)[:-1]])
    survival, variance, rows = 1.0, 0.0, []
    for moment, at_risk, events, left in zip(moments, at_risk_at_moment.tolist(), events_at.tolist(),
                                             leaving.tolist(), strict=True):
        censored = left - events
        if events:
            survival *= 1 - events / at_risk
            variance += events / (at_risk * (at_risk - events)) if at_risk > events else math.inf
        low, high = band(survival, variance)
        rows.append({"time": moment, "at_risk": at_risk, "events": events, "censored": censored,
                     "survival": survival, "low": low, "high": high})
    return pd.DataFrame(rows)


MEDIAN_TOLERANCE = math.sqrt(np.finfo(float).eps)


def km_median(table: pd.DataFrame) -> float | None:
    """First time the survival reaches 50 % or less; where the curve stays at exactly 50 %, the middle between
    that time and its next drop (survival::survfit's rule). None when the curve stays above."""
    reached = table[table["survival"] < 0.5 + MEDIAN_TOLERANCE]
    if not len(reached):
        return None
    first, start = float(reached["survival"].iloc[0]), float(reached["time"].iloc[0])
    lower = reached[reached["survival"] < first]
    if abs(first - 0.5) < MEDIAN_TOLERANCE and len(lower):
        return (start + float(lower["time"].iloc[0])) / 2
    return start


def median_digits(tables: list[pd.DataFrame]) -> int:
    """Decimals for medians: one, or more where the times are small (0.02 years is not 0.0)."""
    from hairline.numbers import auto_digits
    times = np.concatenate([table["time"].to_numpy(dtype=float) for table in tables]) if tables else np.array([])
    return max(1, auto_digits(times[times > 0]))


def at_risk_at(time: Sequence[float], moments: Sequence[float]) -> list[int]:
    """Number still at risk (time not yet passed) at each moment."""
    values = np.asarray(time, dtype=float)
    return [int(np.sum(values >= moment)) for moment in moments]
