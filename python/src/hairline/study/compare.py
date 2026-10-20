"""distribution() and compare(): one variable by group, as a figure, a table, values and a sentence."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import pandas as pd

from hairline.charts.bars import bars
from hairline.charts.spread import spread
from hairline.numbers import format_number, format_p, is_whole
from hairline.stats.tests import contingency_test, kruskal_test, rank_sum_test
from hairline.study.columns import is_missing, level_text, levels, numbers
from hairline.study.describe import counted_rows, group_role, level_numbers, subsets
from hairline.study.result import Result
from hairline.study.summaries import (
    STAT_LABELS,
    check_stats,
    count_share,
    digits_for,
    left_out_text,
    listed,
    overall_only_text,
    summary_numbers,
    summary_text,
)

if TYPE_CHECKING:
    from hairline.study.model import Study

def present_rows(study: Study, variable: str) -> pd.DataFrame:
    """Rows with the variable (and the group, if any) present; the group as text in the study's group key."""
    data = study.data[~is_missing(study.data[variable])]
    if study.group:
        data = data[~is_missing(data[study.group])]
        return data.assign(**{study.group_key: data[study.group].map(level_text)})
    return data.assign(**{study.group_key: study.overall})


def require_values(names: list[str], variable: str, endpoint: str) -> None:
    if not names:
        raise ValueError(f"hairline: {endpoint}: '{variable}' has no values in any group of the study")


def numeric_test(samples: list) -> dict | None:
    if len(samples) == 2:
        return {"method": "Wilcoxon rank-sum", **rank_sum_test(*samples)}
    if len(samples) > 2:
        return {"method": "Kruskal–Wallis", **kruskal_test(samples)}
    return None


def test_text(test: dict) -> str:
    return f"{test['method']}, {format_p(test['p'])}"


def distribution(study: Study, variable: str, stats: Sequence[str] = ("median_iqr",), size: str = "double") -> Result:
    stats = (stats,) if isinstance(stats, str) else tuple(stats)
    check_stats(stats)
    kind = study.kind(variable, "distribution")
    study.require([study.group, variable], "distribution")
    if kind != "numeric":
        raise ValueError(f"hairline: distribution: '{variable}' is categorical; use compare() for its shares")
    study.require_one_row("distribution")
    digits, label = digits_for(numbers(study.data[variable])), study.label_unit(variable)
    whole = is_whole(numbers(study.data[variable]))
    found = {name: summary_numbers(numbers(subset[variable]), stats, int(is_missing(subset[variable]).sum()))
             for name, subset in subsets(study)}
    rows = [[name, format_number(summary["n"], 0), *[summary_text(summary, stat, digits, whole) for stat in stats]]
            for name, summary in found.items()]
    table = pd.DataFrame(rows, columns=["Group", "n", *[STAT_LABELS[stat] for stat in stats]])
    values = {"groups": {row[0]: row[2] for row in rows}}
    data = present_rows(study, variable).assign(**{variable: lambda frame: frame[variable].astype(float)})
    names = list(found)[:-1] if study.group else [study.overall]
    name = study.label(variable)
    title = f"{name} by {str(study.group).replace('_', ' ')}" if study.group else name
    figure = spread(data, study.group_key, variable, order=names, title=title, axis_title=study.measure(variable),
                    size=size)
    shown = rows[:-1] if study.group else rows
    counted = counted_rows(study, {"variable": variable, **group_role(study)}, in_overall=True)
    text = (f"{label}, {STAT_LABELS[stats[0]]}: {listed([f'{row[0]} {row[2]}' for row in shown])}."
            + left_out_text(counted, study.unit, in_overall=True) + overall_only_text(counted))
    return Result(figure, table, values, text, {"rows": counted, "groups": found})


def compare(study: Study, variable: str, size: str = "double") -> Result:
    if not study.group:
        raise ValueError("hairline: compare needs a group; set group= in study()")
    kind = study.kind(variable, "compare")
    if kind == "date":
        raise ValueError(f"hairline: compare: '{variable}' holds dates; follow a measure over it with over_time()")
    study.require([study.group, variable], "compare")
    study.require_one_row("compare")
    if kind == "numeric":
        return compare_numeric(study, variable, size)
    return compare_categorical(study, variable, size)


def compare_numeric(study: Study, variable: str, size: str) -> Result:
    data, label = present_rows(study, variable), study.label_unit(variable)
    digits = digits_for(numbers(data[variable]))
    parts = subsets(study)[:-1]
    found = {name: summary_numbers(numbers(subset[variable]), ("median_iqr",), int(is_missing(subset[variable]).sum()))
             for name, subset in parts}
    names = [name for name in study.groups if found[name]["n"]]
    require_values(names, variable, "compare")
    test = numeric_test([numbers(subset[variable]) for name, subset in parts if name in names])
    whole = is_whole(numbers(data[variable]))
    summaries = [summary_text(found[name], "median_iqr", digits, whole) for name in names]
    rows = [[name, format_number(found[name]["n"], 0), summary] for name, summary in zip(names, summaries, strict=True)]
    rows += [["Test", "", test_text(test)]] if test else []
    values = {"groups": dict(zip(names, summaries, strict=True)),
              **({"test": test["method"], "p": format_p(test["p"])} if test else {})}
    figure = spread(data.assign(**{variable: data[variable].astype(float)}), study.group_key, variable, order=names,
                    title=f"{study.label(variable)} by {str(study.group).replace('_', ' ')}",
                    subtitle=test_text(test) if test else None, axis_title=study.measure(variable), size=size)
    parts = listed([f"{name} {summary}" for name, summary in zip(names, summaries, strict=True)])
    counted = counted_rows(study, {"variable": variable, **group_role(study)})
    text = (f"{label}, median (IQR): {parts}" + (f" ({test_text(test)})." if test else ".")
            + left_out_text(counted, study.unit))
    found = {"rows": counted, "groups": found, **({"test": test} if test else {})}
    return Result(figure, pd.DataFrame(rows, columns=["Group", "n", "median (IQR)"]), values, text, found)


def compare_categorical(study: Study, variable: str, size: str) -> Result:
    data, label = present_rows(study, variable), study.label(variable)
    data = data.assign(**{variable: data[variable].map(level_text)})
    # Categories of the compared groups only: one seen only in a group left out of the study's order is no row.
    kinds = levels(data[data[study.group_key].isin(study.groups)][variable])
    found = {name: level_numbers(subset[variable], kinds) for name, subset in subsets(study)[:-1]}
    names = [name for name in study.groups if found[name]["n"]]
    require_values(names, variable, "compare")
    kinds = [kind for kind in kinds if any(found[name]["counts"][kind] for name in names)]
    counts = [[found[name]["counts"][kind] for name in names] for kind in kinds]
    rows = [[kind, *[count_share(found[name]["counts"][kind], found[name]["n"]) for name in names]] for kind in kinds]
    test = contingency_test(counts) if len(names) > 1 and len(kinds) > 1 else None
    rows += [["Test", test_text(test), *[""] * (len(names) - 1)]] if test else []
    values: dict = {"groups": {name: {row[0]: row[1 + index] for row in rows[:len(kinds)]}
                               for index, name in enumerate(names)}}
    values.update({"test": test["method"], "p": format_p(test["p"])} if test else {})
    figure = bars(data, study.group_key, by=variable, stacked=True, percent=True, horizontal=True, order=names,
                  title=f"{label} by {str(study.group).replace('_', ' ')}", size=size)
    counted = counted_rows(study, {"variable": variable, **group_role(study)})
    text = (f"{label} by {str(study.group).replace('_', ' ')}" + (f": {test_text(test)}." if test else ".")
            + left_out_text(counted, study.unit))
    found = {"rows": counted, "groups": found, **({"test": test} if test else {})}
    return Result(figure, pd.DataFrame(rows, columns=[label, *names]), values, text, found)
