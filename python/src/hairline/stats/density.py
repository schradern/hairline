"""Kernel density, quantiles and jitter for distribution charts, computed the same way in both languages."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

GOLDEN = 0.618034


def quantiles(values: Sequence[float], probabilities: Sequence[float]) -> list[float]:
    """Linear interpolation between order statistics (R's type 7, numpy's default)."""
    return [float(value) for value in np.quantile(np.asarray(values, dtype=float), probabilities)]


def bandwidth(values: Sequence[float]) -> float:
    """Silverman's rule of thumb, as R's bw.nrd0: 0.9 * min(sd, IQR / 1.34) * n^(-1/5)."""
    data = np.asarray(values, dtype=float)
    low, high = quantiles(data, [0.25, 0.75])
    spread = min(float(data.std(ddof=1)), (high - low) / 1.34)
    if spread == 0:
        spread = float(data.std(ddof=1)) or abs(float(data[0])) or 1.0
    return 0.9 * spread * len(data) ** -0.2


def density(values: Sequence[float], points: int = 128) -> tuple[list[float], list[float]] | None:
    """Gaussian kernel density on `points` values spanning the data; None for fewer than two distinct values."""
    data = np.asarray(values, dtype=float)
    if len(np.unique(data)) < 2:
        return None
    width = bandwidth(data)
    grid = np.linspace(data.min(), data.max(), points)
    scaled = (grid[:, None] - data[None, :]) / width
    height = np.exp(-0.5 * scaled ** 2).sum(axis=1) / (len(data) * width * math.sqrt(2 * math.pi))
    return [float(value) for value in grid], [float(value) for value in height]


def jitter_offsets(count: int) -> list[float]:
    """Offsets in [-0.5, 0.5] from the golden-ratio sequence: spread evenly, the same on every run."""
    return [((index + 1) * GOLDEN) % 1 - 0.5 for index in range(count)]


def level_quantiles(values: Sequence[float], probabilities: Sequence[float]) -> list[float]:
    """Quantiles that stay on the data's levels (R's type 1, numpy's inverted_cdf): the smallest value reached by
    at least that share of the values. Of daily peaks, the 0.9 quantile is the staffing that is enough on 9 of 10
    days; of counts of people, the median is a whole person."""
    data = np.asarray(values, dtype=float)
    return [float(value) for value in np.quantile(data, probabilities, method="inverted_cdf")]


def median_gap(values: Sequence[float], share: float, least: int = 10) -> tuple[float, float] | None:
    """The two levels a median falls between when it matches neither and each holds more than `share` of the
    values (doses of 25 and 50 mg, median 35); None otherwise, and for fewer than `least` values, whose median
    falls between two of them by chance."""
    data = np.asarray(values, dtype=float)
    if len(data) < least:
        return None
    middle = float(np.median(data))
    below, above = data[data < middle], data[data > middle]
    if not len(below) or not len(above) or (data == middle).any():
        return None
    low, high = float(below.max()), float(above.min())
    if (data == low).mean() > share and (data == high).mean() > share:
        return low, high
    return None


def top_levels(values: Sequence[float], count: int) -> list[tuple[float, float]]:
    """The `count` most frequent values with their shares, most frequent first (ties: the smaller value first)."""
    levels, counts = np.unique(np.asarray(values, dtype=float), return_counts=True)
    ranked = sorted(zip(levels, counts, strict=True), key=lambda pair: (-pair[1], pair[0]))[:count]
    return [(float(level), float(found) / len(values)) for level, found in ranked]
