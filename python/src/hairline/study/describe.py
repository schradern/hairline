"""describe(): Table 1 by group, values per variable, a counts sentence and an overview of the numeric variables."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import pandas as pd

from hairline import entities
from hairline.figure import HairlineFigure, figure
from hairline.numbers import format_number
from hairline.stats.density import quantiles
from hairline.study.columns import is_missing, level_text, levels, numbers
from hairline.study.result import Result
from hairline.study.summaries import STAT_LABELS, check_stats, count_share, digits_for, numeric_text
from hairline.tokens import load_tokens

if TYPE_CHECKING:
    from hairline.study.model import Study

OVERALL = "Overall"


def subsets(study: Study) -> list[tuple[str, pd.DataFrame]]:
    """Each group's rows, then all rows as Overall; without a group only Overall."""
    if not study.group:
        return [(OVERALL, study.data)]
    labels = study.data[study.group].map(lambda value: None if pd.isna(value) else level_text(value))
    return [(name, study.data[labels == name]) for name in study.groups] + [(OVERALL, study.data)]


def numeric_rows(study: Study, name: str, parts: list, stats: Sequence[str]) -> tuple[list[list[str]], dict]:
    digits = digits_for(numbers(study.data[name]))
    rows, values = [], {}
    for stat in stats:
        texts = [numeric_text(numbers(rows_[name]), stat, digits, int(is_missing(rows_[name]).sum()))
                 for _, rows_ in parts]
        rows.append([f"{study.label(name)}, {STAT_LABELS[stat]}", *texts])
        values.setdefault(name, dict(zip([label for label, _ in parts], texts, strict=True)))
    return rows, values


def categorical_rows(study: Study, name: str, parts: list) -> tuple[list[list[str]], dict]:
    names = levels(study.data[name])
    rows = [[f"{study.label(name)}, n (%)", *([""] * len(parts))]]
    values: dict[str, dict[str, str]] = {label: {} for label, _ in parts}
    for level in names:
        texts = []
        for label, subset in parts:
            present = subset[name][~is_missing(subset[name])].map(level_text)
            texts.append(count_share(int((present == level).sum()), len(present)))
            values[label][level] = texts[-1]
        rows.append([f"  {level}", *texts])
    return rows, {name: values}


def describe(study: Study, stats: Sequence[str] = ("median_iqr",), size: str = "double") -> Result:
    stats = tuple(stats)
    check_stats(stats)
    study.require([study.group, *study.variables], "describe")
    parts = subsets(study)
    counts = [format_number(len(rows), 0) for _, rows in parts]
    table, values = [["n", *counts]], {"n": dict(zip([label for label, _ in parts], counts, strict=True))}
    for name in study.variables:
        rows, found = (numeric_rows(study, name, parts, stats) if study.types[name] == "numeric"
                       else categorical_rows(study, name, parts))
        table += rows
        values.update(found)
    frame = pd.DataFrame(table, columns=["Characteristic", *[label for label, _ in parts]])
    return Result(overview(study, parts, size), frame, values, counts_text(study, parts, counts))


def counts_text(study: Study, parts: list, counts: list[str]) -> str:
    total = f"{counts[-1]} {study.unit}"
    if not study.group:
        return f"{total}."
    groups = [f"{count} in {label}" for (label, _), count in zip(parts[:-1], counts[:-1], strict=True)]
    return f"{total}: {', '.join(groups[:-1])} and {groups[-1]}." if len(groups) > 1 else f"{total}: {groups[0]}."


def overview(study: Study, parts: list, size: str) -> HairlineFigure | None:
    """One panel per numeric variable: median and interquartile range per group, first group on top."""
    numeric = [name for name in study.variables if study.types[name] == "numeric"]
    if not numeric:
        return None
    shown = parts[:-1] if study.group else parts
    names = [label for label, _ in shown]
    title = f"Characteristics by {str(study.group).replace('_', ' ')}" if study.group else "Characteristics"
    rules = load_tokens()["study"]
    columns = min(len(numeric), rules["overview_columns"])
    rows = -(-len(numeric) // columns)
    height = rules["overview_frame_mm"] + rows * (rules["overview_panel_mm"] + len(shown) * rules["overview_row_mm"])
    result = figure(title, subtitle="Median and interquartile range", size=size, height_mm=height,
                    panels=len(numeric), layout="pair", columns=columns)
    with entities.chart(names if study.group else [], None):
        colors = entities.colors_for(names, None) if study.group else {names[0]: result.settings.palette[0]}
        for index, name in enumerate(numeric):
            ax = result.axes[index]
            for position, (label, rows) in enumerate(shown):
                low, middle, high = quantiles(numbers(rows[name]), [0.25, 0.5, 0.75])
                y = len(shown) - 1 - position
                ax.plot([low, high], [y, y], color=colors[label], solid_capstyle="butt")
                ax.scatter([middle], [y], color=colors[label], zorder=3)
            result.categories(index, list(reversed(names)), "y")
            result.panel_header(index, study.label(name))
            ax.set_ylim(-0.6, len(shown) - 0.4)
    return result
