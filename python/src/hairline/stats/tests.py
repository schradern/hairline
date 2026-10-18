"""Tests and fits the charts compute from raw data, matching R's survdiff, wilcox.test, lm and cor.test."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from hairline.stats.distributions import chi2_sf, normal_cdf, t_cdf, t_quantile


def ranks(values: Sequence[float]) -> np.ndarray:
    """Ranks with ties sharing their average rank."""
    data = np.asarray(values, dtype=float)
    order = np.argsort(data, kind="mergesort")
    result = np.empty(len(data))
    position = 0
    while position < len(data):
        end = position
        while end + 1 < len(data) and data[order[end + 1]] == data[order[position]]:
            end += 1
        result[order[position:end + 1]] = (position + end) / 2 + 1
        position = end + 1
    return result


def rank_sum(first: Sequence[float], second: Sequence[float]) -> float:
    """Two-sided Wilcoxon rank-sum p, normal approximation with tie and continuity correction."""
    count_x, count_y = len(first), len(second)
    combined = ranks(list(first) + list(second))
    statistic = combined[:count_x].sum() - count_x * (count_x + 1) / 2
    total = count_x + count_y
    _, ties = np.unique(combined, return_counts=True)
    sigma = math.sqrt(count_x * count_y / 12 * ((total + 1) - (ties ** 3 - ties).sum() / (total * (total - 1))))
    shift = statistic - count_x * count_y / 2
    z = (shift - math.copysign(0.5, shift) if shift else 0.0) / sigma
    return 2 * min(normal_cdf(z), 1 - normal_cdf(z))


def logrank(time: Sequence[float], event: Sequence[int], group: Sequence[str]) -> dict:
    """Log-rank test over all groups (order of appearance): chi-square, degrees of freedom and p."""
    time, event = np.asarray(time, dtype=float), np.asarray(event, dtype=float)
    labels = list(dict.fromkeys(group))
    member = np.array([[name == label for name in group] for label in labels])
    observed_minus_expected, variance = np.zeros(len(labels)), np.zeros((len(labels), len(labels)))
    for moment in np.unique(time[event == 1]):
        at_risk = (member & (time >= moment)).sum(axis=1).astype(float)
        deaths = (member & (time == moment) & (event == 1)).sum(axis=1).astype(float)
        n, d = at_risk.sum(), deaths.sum()
        share = at_risk / n
        observed_minus_expected += deaths - d * share
        if n > 1:
            variance += d * (n - d) / (n - 1) * (np.diag(share) - np.outer(share, share))
    keep = len(labels) - 1
    statistic = float(observed_minus_expected[:keep] @ np.linalg.solve(variance[:keep, :keep],
                                                                       observed_minus_expected[:keep]))
    return {"chisq": statistic, "df": keep, "p": chi2_sf(statistic, keep)}


def linear_fit(x: Sequence[float], y: Sequence[float]) -> dict:
    """Ordinary least squares with the slope's standard error and what the 95 % band of the mean needs."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    count, mean_x = len(x), x.mean()
    spread = ((x - mean_x) ** 2).sum()
    slope = ((x - mean_x) * (y - y.mean())).sum() / spread
    intercept = y.mean() - slope * mean_x
    residual = math.sqrt(((y - intercept - slope * x) ** 2).sum() / (count - 2))
    return {"slope": float(slope), "intercept": float(intercept), "slope_se": residual / math.sqrt(spread),
            "residual": residual, "count": count, "mean_x": float(mean_x), "spread": float(spread),
            "t": t_quantile(0.975, count - 2)}


def fit_band(fit: dict, xs: Sequence[float]) -> tuple[list[float], list[float], list[float]]:
    """Fitted values and the 95 % confidence band of the mean at `xs`."""
    centre = [fit["intercept"] + fit["slope"] * x for x in xs]
    half = [fit["t"] * fit["residual"] * math.sqrt(1 / fit["count"] + (x - fit["mean_x"]) ** 2 / fit["spread"])
            for x in xs]
    pairs = list(zip(centre, half, strict=True))
    return centre, [value - spread for value, spread in pairs], [value + spread for value, spread in pairs]


def pearson(x: Sequence[float], y: Sequence[float]) -> tuple[float, float]:
    """Correlation and its two-sided p (t test with n - 2 degrees of freedom)."""
    r = float(np.corrcoef(np.asarray(x, dtype=float), np.asarray(y, dtype=float))[0, 1])
    count = len(x)
    if abs(r) >= 1:
        return r, 0.0
    statistic = r * math.sqrt((count - 2) / (1 - r * r))
    return r, 2 * (1 - t_cdf(abs(statistic), count - 2))


def spearman(x: Sequence[float], y: Sequence[float]) -> tuple[float, float]:
    return pearson(ranks(x), ranks(y))


def egger(estimate: Sequence[float], se: Sequence[float]) -> float:
    """Egger's test for funnel asymmetry: p of the intercept when estimate / se is regressed on 1 / se."""
    se = np.asarray(se, dtype=float)
    precision, standardised = 1 / se, np.asarray(estimate, dtype=float) / se
    fit = linear_fit(precision, standardised)
    intercept_se = fit["residual"] * math.sqrt(1 / fit["count"] + fit["mean_x"] ** 2 / fit["spread"])
    return 2 * (1 - t_cdf(abs(fit["intercept"] / intercept_se), fit["count"] - 2))


def kruskal(samples: Sequence[Sequence[float]]) -> float:
    """Kruskal–Wallis p over two or more samples, with the tie correction (as R's kruskal.test)."""
    sizes = [len(sample) for sample in samples]
    combined = ranks([value for sample in samples for value in sample])
    total, bounds = sum(sizes), np.cumsum([0, *sizes])
    statistic = 12 / (total * (total + 1)) * sum(combined[start:end].sum() ** 2 / (end - start)
                                                 for start, end in zip(bounds[:-1], bounds[1:], strict=True))
    statistic -= 3 * (total + 1)
    _, ties = np.unique(combined, return_counts=True)
    statistic /= 1 - (ties ** 3 - ties).sum() / (total ** 3 - total)
    return chi2_sf(float(statistic), len(samples) - 1)


def chi_square(counts: Sequence[Sequence[float]]) -> float:
    """Pearson χ² test of independence on a table of counts, without continuity correction."""
    observed = np.asarray(counts, dtype=float)
    expected = np.outer(observed.sum(axis=1), observed.sum(axis=0)) / observed.sum()
    used = expected > 0
    statistic = float(((observed[used] - expected[used]) ** 2 / expected[used]).sum())
    return chi2_sf(statistic, (observed.shape[0] - 1) * (observed.shape[1] - 1))
