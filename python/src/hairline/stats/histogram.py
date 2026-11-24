"""Histogram bins a reader can name: a round width (1, 2, 2.5 or 5 times a power of ten), edges on its multiples."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from hairline.stats.density import quantiles
from hairline.tokens import load_tokens


def round_width(raw: float, whole: bool) -> float:
    """The round width nearest `raw` on a log scale (5.4 years gives 5, not 10); whole numbers keep whole widths
    (no 2.5 years)."""
    multipliers = [step for step in load_tokens()["ticks"]["multipliers"] if not whole or step != 2.5]
    power = 10.0 ** math.floor(math.log10(raw))
    candidates = [step * power for step in [*multipliers, 10]]
    width = min(candidates, key=lambda candidate: abs(math.log(candidate / raw)))
    return max(width, 1.0) if whole else width


def bin_width(values: Sequence[float], whole: bool) -> float:
    """Freedman–Diaconis width, kept between the fewest and most bins the tokens allow, then rounded."""
    rules = load_tokens()["profile"]
    low, high = float(np.min(values)), float(np.max(values))
    span = high - low
    if span <= 0:
        return 1.0
    q1, q3 = quantiles(values, [0.25, 0.75])
    raw = 2 * (q3 - q1) / len(values) ** (1 / 3) if q3 > q1 else span / rules["min_bins"]
    raw = min(max(raw, span / rules["max_bins"]), span / rules["min_bins"])
    return round_width(raw, whole)


def bin_edges(values: Sequence[float], whole: bool) -> np.ndarray:
    """Edges of round bins covering every value; each bin holds [edge, next edge)."""
    values = np.asarray(values, dtype=float)
    width = bin_width(values, whole)
    # Bins one whole number wide sit on it (stay of 4 days spans 3.5 to 4.5), wider bins start on their multiple.
    offset = 0.5 if whole and width == 1 else 0.0
    start = math.floor(float(values.min()) / width + offset) * width - offset
    count = int(math.floor((float(values.max()) - start) / width + 1e-9)) + 1
    return start + width * np.arange(count + 1)


def counts_in(values: Sequence[float], edges: np.ndarray) -> list[int]:
    """How many values fall in each bin of `edges` (none for an empty group)."""
    counts, _ = np.histogram(np.asarray(values, dtype=float), bins=edges)
    return [int(value) for value in counts]


def histogram(values: Sequence[float], whole: bool) -> tuple[list[float], list[int], float]:
    """Left edges, counts and the width of round bins over `values`."""
    edges = bin_edges(values, whole)
    return [float(edge) for edge in edges[:-1]], counts_in(values, edges), float(edges[1] - edges[0])
