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


def rank_sum_test(first: Sequence[float], second: Sequence[float]) -> dict:
    """Two-sided Wilcoxon rank-sum test: W (as R's wilcox.test) and p, normal approximation with tie and continuity
    correction; p is NaN when every value ties, which leaves the test undefined (as R's wilcox.test)."""
    count_x, count_y = len(first), len(second)
    combined = ranks(list(first) + list(second))
    statistic = float(combined[:count_x].sum() - count_x * (count_x + 1) / 2)
    total = count_x + count_y
    _, ties = np.unique(combined, return_counts=True)
    sigma = math.sqrt(count_x * count_y / 12 * ((total + 1) - (ties ** 3 - ties).sum() / (total * (total - 1))))
    if sigma == 0:
        return {"statistic": statistic, "p": math.nan}
    shift = statistic - count_x * count_y / 2
    z = (shift - math.copysign(0.5, shift) if shift else 0.0) / sigma
    return {"statistic": statistic, "p": 2 * min(normal_cdf(z), 1 - normal_cdf(z))}


def rank_sum(first: Sequence[float], second: Sequence[float]) -> float:
    """The rank-sum p; NaN when every value ties."""
    return rank_sum_test(first, second)["p"]


def logrank(time: Sequence[float], event: Sequence[int], group: Sequence[str]) -> dict:
    """Log-rank test over all groups (order of appearance): chi-square, degrees of freedom and p. As
    survival::survdiff, only groups with expected events take part, one of them left out of the quadratic form. With
    fewer than two such groups, or a singular variance (every event at one time), the test is undefined: p is NaN."""
    time, event = np.asarray(time, dtype=float), np.asarray(event, dtype=float)
    labels = list(dict.fromkeys(group))
    member = np.array([[name == label for name in group] for label in labels])
    observed_minus_expected, variance = np.zeros(len(labels)), np.zeros((len(labels), len(labels)))
    expected = np.zeros(len(labels))
    undefined = {"chisq": math.nan, "df": len(labels) - 1, "p": math.nan}
    for moment in np.unique(time[event == 1]):
        at_risk = (member & (time >= moment)).sum(axis=1).astype(float)
        deaths = (member & (time == moment) & (event == 1)).sum(axis=1).astype(float)
        n, d = at_risk.sum(), deaths.sum()
        share = at_risk / n
        expected += d * share
        observed_minus_expected += deaths - d * share
        if n > 1:
            variance += d * (n - d) / (n - 1) * (np.diag(share) - np.outer(share, share))
    kept = np.flatnonzero(expected > 0)
    if len(kept) < 2:
        return undefined
    used = kept[1:]
    try:
        statistic = float(observed_minus_expected[used] @ np.linalg.solve(variance[np.ix_(used, used)],
                                                                          observed_minus_expected[used]))
    except np.linalg.LinAlgError:
        return undefined
    return {"chisq": statistic, "df": len(used), "p": chi2_sf(statistic, len(used))}


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
    """Egger's test for funnel asymmetry: p of the intercept when estimate / se is regressed on 1 / se. NaN
    (undefined) with fewer than three studies, one standard error for all, or a perfect fit."""
    se = np.asarray(se, dtype=float)
    if len(se) < 3 or len(np.unique(se)) < 2:
        return math.nan
    precision, standardised = 1 / se, np.asarray(estimate, dtype=float) / se
    fit = linear_fit(precision, standardised)
    intercept_se = fit["residual"] * math.sqrt(1 / fit["count"] + fit["mean_x"] ** 2 / fit["spread"])
    if intercept_se == 0:
        return math.nan
    return 2 * (1 - t_cdf(abs(fit["intercept"] / intercept_se), fit["count"] - 2))


def kruskal_test(samples: Sequence[Sequence[float]]) -> dict:
    """Kruskal–Wallis test over two or more samples, with the tie correction (as R's kruskal.test): H, degrees of
    freedom and p; H and p are NaN when every value ties."""
    sizes, df = [len(sample) for sample in samples], len(samples) - 1
    combined = ranks([value for sample in samples for value in sample])
    total, bounds = sum(sizes), np.cumsum([0, *sizes])
    statistic = 12 / (total * (total + 1)) * sum(combined[start:end].sum() ** 2 / (end - start)
                                                 for start, end in zip(bounds[:-1], bounds[1:], strict=True))
    statistic -= 3 * (total + 1)
    _, ties = np.unique(combined, return_counts=True)
    correction = 1 - (ties ** 3 - ties).sum() / (total ** 3 - total)
    if correction == 0:
        return {"statistic": math.nan, "df": df, "p": math.nan}
    statistic = float(statistic / correction)
    return {"statistic": statistic, "df": df, "p": chi2_sf(statistic, df)}


def kruskal(samples: Sequence[Sequence[float]]) -> float:
    """The Kruskal–Wallis p; NaN when every value ties."""
    return kruskal_test(samples)["p"]


def chi_square_test(counts: Sequence[Sequence[float]]) -> dict:
    """Pearson χ² test of independence on a table of counts, without continuity correction: χ², degrees of freedom
    and p."""
    observed = np.asarray(counts, dtype=float)
    expected = np.outer(observed.sum(axis=1), observed.sum(axis=0)) / observed.sum()
    used = expected > 0
    statistic = float(((observed[used] - expected[used]) ** 2 / expected[used]).sum())
    df = (observed.shape[0] - 1) * (observed.shape[1] - 1)
    return {"statistic": statistic, "df": df, "p": chi2_sf(statistic, df)}


def chi_square(counts: Sequence[Sequence[float]]) -> float:
    return chi_square_test(counts)["p"]
