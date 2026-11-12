"""compare=: each group against a reference group or the group before it, written as numbers beside the others
(never over the data): the difference with its 95 % CI and p, the test named in the caption. The test follows the
chart's centre: with the median the Hodges–Lehmann shift (distribution-free CI) and the Wilcoxon rank-sum p, with the
mean alone the difference in means and Welch's t-test. The R package mirrors this in comparisons.R."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from hairline.charts.summaries import DASH, Numbers
from hairline.numbers import format_p, word
from hairline.stats.distributions import t_cdf, t_quantile
from hairline.stats.tests import rank_sum

ADJACENT = "adjacent"
# The normal quantile of a two-sided 95 % interval, as R's qnorm(0.975).
Z_975 = 1.959963984540054
# Pairwise differences the shift computes at most (two groups of 3,000 values); beyond, its CI is left out.
MAX_PAIRS = 9_000_000


def check_compare(compare: str | None, names: Sequence[str], chart: str) -> str | None:
    """A group to compare against, or "adjacent"; None compares nothing."""
    if compare is None:
        return None
    compare = str(compare)
    if compare == "all":
        raise ValueError(f"hairline: {chart}: compare='all' would need a number for every pair, which no row can "
                         f"hold; compare against one group (compare={names[0]!r}) or 'adjacent'")
    if compare != ADJACENT and compare not in names:
        raise ValueError(f"hairline: {chart}: compare names {compare!r}, which is not a group; use 'adjacent' or one "
                         f"of: {', '.join(names)}")
    return compare


def compare_method(marks: Sequence[str]) -> str:
    """'means' when the chart's centre is the mean alone, 'shift' (rank-based) otherwise."""
    return "means" if "mean" in marks and "median" not in marks else "shift"


def welch(first: np.ndarray, second: np.ndarray) -> dict:
    """Difference in means (first minus second) with Welch's 95 % CI and two-sided p; NaN where a group has fewer
    than two values or neither varies."""
    count_x, count_y = len(first), len(second)
    difference = float(np.mean(first) - np.mean(second))
    if count_x < 2 or count_y < 2:
        return {"estimate": difference, "low": math.nan, "high": math.nan, "p": math.nan}
    share_x, share_y = np.var(first, ddof=1) / count_x, np.var(second, ddof=1) / count_y
    error = math.sqrt(share_x + share_y)
    if error == 0:
        return {"estimate": difference, "low": math.nan, "high": math.nan, "p": math.nan}
    freedom = (share_x + share_y) ** 2 / (share_x ** 2 / (count_x - 1) + share_y ** 2 / (count_y - 1))
    half = t_quantile(0.975, freedom) * error
    p = 2 * (1 - t_cdf(abs(difference) / error, freedom))
    return {"estimate": difference, "low": difference - half, "high": difference + half, "p": min(1.0, p)}


def shift(first: np.ndarray, second: np.ndarray) -> dict:
    """Hodges–Lehmann shift (first minus second): the median of every pairwise difference, its distribution-free 95 %
    CI from the order statistics of those differences (normal approximation, as Bauer 1972), and the rank-sum p."""
    count_x, count_y = len(first), len(second)
    pairs = count_x * count_y
    p = rank_sum(first, second)
    if pairs > MAX_PAIRS:
        estimate = float(np.median(first) - np.median(second))
        return {"estimate": estimate, "low": math.nan, "high": math.nan, "p": p}
    differences = np.sort(np.subtract.outer(first, second).ravel())
    estimate = float(np.median(differences))
    rank = math.floor(pairs / 2 - Z_975 * math.sqrt(pairs * (count_x + count_y + 1) / 12))
    if rank < 1:
        return {"estimate": estimate, "low": math.nan, "high": math.nan, "p": p}
    return {"estimate": estimate, "low": float(differences[rank - 1]), "high": float(differences[pairs - rank]),
            "p": p}


def p_text(value: float, locale: str | None = None) -> str:
    """A p as a key number's value: '0.004', '< 0.001'; a dash where the test is undefined."""
    if math.isnan(value):
        return DASH
    return format_p(value, locale).removeprefix("p ").removeprefix("= ")


def difference_text(found: dict, numbers: Numbers, method: str) -> str:
    number = numbers[1] if method == "means" else numbers[0]
    if math.isnan(found["low"]):
        return number(found["estimate"])
    return f"{number(found['estimate'])} [{number(found['low'])}; {number(found['high'])}]"


def comparison_pairs(groups: Sequence[tuple[str, np.ndarray]], compare: str, method: str, numbers: Numbers,
                     locale: str | None = None) -> dict[str, list[list[str]]]:
    """Each group's Δ and p as key-number pairs, in the groups' order: against the reference ('Reference' on its own
    row) or against the group before it (a dash on the first). A reference absent here leaves dashes."""
    values = dict(groups)
    label = word("difference", locale)
    found = {}
    for index, (name, data) in enumerate(groups):
        other = (groups[index - 1][0] if index else None) if compare == ADJACENT else compare
        if compare != ADJACENT and name == compare:
            found[name] = [[label, word("reference_group", locale)], ["p", DASH]]
        elif other is None or other not in values or not len(data) or not len(values[other]):
            found[name] = [[label, DASH], ["p", DASH]]
        else:
            test = (welch if method == "means" else shift)(np.asarray(data, float), np.asarray(values[other], float))
            found[name] = [[label, difference_text(test, numbers, method)], ["p", p_text(test["p"], locale)]]
    return found


def compare_caption(compare: str, method: str, comparisons: int, locale: str | None = None) -> str:
    """The test named for the caption, and that several p values are not adjusted."""
    against = word("against_previous", locale) if compare == ADJACENT else word("against_group", locale,
                                                                                  name=compare)
    text = word(f"compare_{method}", locale, against=against)
    return f"{text} {word('unadjusted', locale)}" if comparisons > 1 else text


def compared_sections(rows: list[dict], values: dict, compare: str, method: str, numbers: Numbers,
                      shown: dict | None = None) -> int:
    """Rows drawn in sections (spread, dot plot blocks): each section's groups compared within it, in row order,
    their Δ and p added to each row's pairs; returns the number of comparisons. `shown` names a row's group where
    its key differs (a facet's "2025 · Unit A" is the group "Unit A")."""
    shown = shown or {}
    count = 0
    for section in dict.fromkeys(row.get("section") for row in rows):
        members = [row for row in rows if row.get("section") == section]
        groups = [(shown.get(row["name"], row["name"]), values[row["name"]]) for row in members]
        found = comparison_pairs(groups, compare, method, numbers)
        for row, (name, _) in zip(members, groups, strict=True):
            row["pairs"] = row["pairs"] + found[name]
        count += sum(text != DASH and text != word("reference_group") for _, text in
                     (found[name][0] for name, _ in groups))
    return count


def section_comparisons(rows: list[dict], values: dict, compare: str | None, marks: Sequence[str], numbers: Numbers,
                        chart: str, group_names: dict | None = None) -> str | None:
    """Each row's Δ and p against `compare` within its section, added to its numbers; the caption note naming the
    test. None without compare."""
    group_names = dict(group_names or {})
    names = list(dict.fromkeys(group_names.get(row["name"], row["name"]) for row in rows))
    compare = check_compare(compare, names, chart)
    if compare is None:
        return None
    method = compare_method(marks)
    count = compared_sections(rows, values, compare, method, numbers, group_names)
    return compare_caption(compare, method, count)
