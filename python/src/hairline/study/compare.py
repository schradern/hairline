"""distribution() and compare(): one variable by group, as a figure, a table, values and a sentence."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import pandas as pd

from hairline.charts.bars import bars
from hairline.charts.spread import spread
from hairline.numbers import format_number, format_p, is_whole
from hairline.stats.tests import chi_square, kruskal, rank_sum
from hairline.study.columns import is_missing, level_text, levels, numbers
from hairline.study.describe import OVERALL, subsets
from hairline.study.result import Result
from hairline.study.summaries import STAT_LABELS, check_stats, count_share, digits_for, numeric_text

if TYPE_CHECKING:
    from hairline.study.model import Study

GROUP = "_group"


def listed(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def present_rows(study: Study, variable: str) -> pd.DataFrame:
    """Rows with the variable (and the group, if any) present; the group as text in GROUP."""
    data = study.data[~is_missing(study.data[variable])]
    if study.group:
        data = data[~is_missing(data[study.group])]
        return data.assign(**{GROUP: data[study.group].map(level_text)})
    return data.assign(**{GROUP: OVERALL})


def numeric_test(samples: list) -> tuple[str, str] | None:
    if len(samples) == 2:
        return "Wilcoxon rank-sum", format_p(rank_sum(*samples))
    if len(samples) > 2:
        return "Kruskal–Wallis", format_p(kruskal(samples))
    return None


def distribution(study: Study, variable: str, stats: Sequence[str] = ("median_iqr",), size: str = "double") -> Result:
    stats = (stats,) if isinstance(stats, str) else tuple(stats)
    check_stats(stats)
    kind = study.kind(variable, "distribution")
    study.require([study.group, variable], "distribution")
    if kind != "numeric":
        raise ValueError(f"hairline: distribution: '{variable}' is categorical; use compare() for its shares")
    digits, label = digits_for(numbers(study.data[variable])), study.label_unit(variable)
    whole = is_whole(numbers(study.data[variable]))
    parts = subsets(study)
    rows = [[name, format_number(int((~is_missing(subset[variable])).sum()), 0),
             *[numeric_text(numbers(subset[variable]), stat, digits, int(is_missing(subset[variable]).sum()), whole)
               for stat in stats]] for name, subset in parts]
    table = pd.DataFrame(rows, columns=["Group", "n", *[STAT_LABELS[stat] for stat in stats]])
    values = {row[0]: row[2] for row in rows}
    data = present_rows(study, variable).assign(**{variable: lambda frame: frame[variable].astype(float)})
    names = [name for name, _ in parts[:-1]] if study.group else [OVERALL]
    name = study.label(variable)
    title = f"{name} by {str(study.group).replace('_', ' ')}" if study.group else name
    figure = spread(data, GROUP, variable, order=names, title=title, axis_title=study.measure(variable), size=size)
    shown = rows[:-1] if study.group else rows
    text = f"{label}, {STAT_LABELS[stats[0]]}: {listed([f'{row[0]} {row[2]}' for row in shown])}."
    return Result(figure, table, values, text)


def compare(study: Study, variable: str, size: str = "double") -> Result:
    if not study.group:
        raise ValueError("hairline: compare needs a group; set group= in study()")
    kind = study.kind(variable, "compare")
    if kind == "date":
        raise ValueError(f"hairline: compare: '{variable}' holds dates; follow a measure over it with over_time()")
    study.require([study.group, variable], "compare")
    if kind == "numeric":
        return compare_numeric(study, variable, size)
    return compare_categorical(study, variable, size)


def compare_numeric(study: Study, variable: str, size: str) -> Result:
    data, label = present_rows(study, variable), study.label_unit(variable)
    digits = digits_for(numbers(data[variable]))
    names = [name for name in study.groups if (data[GROUP] == name).any()]
    samples = [numbers(data[data[GROUP] == name][variable]) for name in names]
    summaries = [numeric_text(sample, "median_iqr", digits, 0) for sample in samples]
    test = numeric_test(samples)
    rows = [[name, format_number(len(sample), 0), summary] for name, sample, summary in zip(names, samples, summaries,
                                                                                            strict=True)]
    rows += [["Test", "", f"{test[0]}, {test[1]}"]] if test else []
    values = {**dict(zip(names, summaries, strict=True)), **({"test": test[0], "p": test[1]} if test else {})}
    figure = spread(data.assign(**{variable: data[variable].astype(float)}), GROUP, variable, order=names,
                    title=f"{study.label(variable)} by {str(study.group).replace('_', ' ')}",
                    subtitle=f"{test[0]}, {test[1]}" if test else None, axis_title=study.measure(variable), size=size)
    parts = listed([f"{name} {summary}" for name, summary in zip(names, summaries, strict=True)])
    text = f"{label}, median (IQR): {parts}" + (f" ({test[0]}, {test[1]})." if test else ".")
    return Result(figure, pd.DataFrame(rows, columns=["Group", "n", "median (IQR)"]), values, text)


def compare_categorical(study: Study, variable: str, size: str) -> Result:
    data, label = present_rows(study, variable), study.label(variable)
    data = data.assign(**{variable: data[variable].map(level_text)})
    names = [name for name in study.groups if (data[GROUP] == name).any()]
    kinds = levels(data[variable])
    counts = [[int(((data[GROUP] == name) & (data[variable] == kind)).sum()) for name in names] for kind in kinds]
    totals = [int((data[GROUP] == name).sum()) for name in names]
    rows = [[kind, *[count_share(count, total) for count, total in zip(row, totals, strict=True)]]
            for kind, row in zip(kinds, counts, strict=True)]
    test = ("Chi-squared", format_p(chi_square(counts))) if len(names) > 1 and len(kinds) > 1 else None
    rows += [["Test", f"{test[0]}, {test[1]}", *[""] * (len(names) - 1)]] if test else []
    values: dict = {name: {row[0]: row[1 + index] for row in rows[:len(kinds)]} for index, name in enumerate(names)}
    values.update({"test": test[0], "p": test[1]} if test else {})
    figure = bars(data, GROUP, by=variable, stacked=True, percent=True, horizontal=True, order=names,
                  title=f"{label} by {str(study.group).replace('_', ' ')}", size=size)
    text = f"{label} by {str(study.group).replace('_', ' ')}" + (f": {test[0]}, {test[1]}." if test else ".")
    return Result(figure, pd.DataFrame(rows, columns=[label, *names]), values, text)
