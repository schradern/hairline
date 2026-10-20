"""describe(): Table 1 by group, values per variable, a counts sentence and an overview of the numeric variables."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import pandas as pd
from matplotlib.patches import Rectangle

from hairline import entities
from hairline.figure import HairlineFigure, figure
from hairline.marks import FIXED_ID, STATIC_ID, lone_color
from hairline.numbers import format_number, is_whole
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
    digits, whole = digits_for(numbers(study.data[name])), is_whole(numbers(study.data[name]))
    rows, values = [], {}
    for stat in stats:
        texts = [numeric_text(numbers(rows_[name]), stat, digits, int(is_missing(rows_[name]).sum()), whole)
                 for _, rows_ in parts]
        rows.append([f"{study.label_unit(name)}, {STAT_LABELS[stat]}", *texts])
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


def overview_row(ax, values, y: float, color: str, style: dict) -> None:
    """One spread row on axes: range line, interquartile band, median dot (as the spread chart draws them); a group
    without values keeps its row empty, as its table cell shows a dash."""
    if not len(values):
        return
    rules = load_tokens()["spread"]
    low, q1, middle, q3, high = quantiles(values, [0, 0.25, 0.5, 0.75, 1])
    ax.plot([low, high], [y, y], color=style["faint"], linewidth=style["leader"], gid=FIXED_ID,
            solid_capstyle="butt", label="_nolegend_")
    ax.add_patch(Rectangle((q1, y - rules["band"] / 2), q3 - q1, rules["band"], facecolor=color, edgecolor="none",
                           alpha=rules["band_opacity"], linewidth=0))
    ax.scatter([middle], [y], color=color, zorder=3, gid=STATIC_ID)


def overview(study: Study, parts: list, size: str) -> HairlineFigure | None:
    """One panel per numeric variable: spread rows per group, first group on top, the unit under each axis."""
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
    result = figure(title, subtitle="Range, interquartile range and median", size=size, height_mm=height,
                    panels=len(numeric), layout="pair", columns=columns)
    style = {"faint": result.settings.neutral["faint"],
             "leader": load_tokens()["reference"]["width"] * result.settings.base_size}
    with entities.chart(names if study.group else [], None):
        colors = entities.colors_for(names, None) if study.group else {names[0]: lone_color(result.settings)}
        for index, name in enumerate(numeric):
            ax = result.axes[index]
            for position, (label, subset) in enumerate(shown):
                overview_row(ax, numbers(subset[name]), len(shown) - 1 - position, colors[label], style)
            result.categories(index, list(reversed(names)), "y")
            result.panel_header(index, study.label(name), x_title=study.measure(name))
            ax.set_ylim(-0.6, len(shown) - 0.4)
    return result
