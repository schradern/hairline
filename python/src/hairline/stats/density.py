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
