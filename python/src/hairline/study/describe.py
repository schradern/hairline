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
from hairline.study.result import Result, figure_for
from hairline.study.summaries import (
    STAT_LABELS,
    check_stats,
    count_share,
    counted_text,
    digits_for,
    listed,
    overall_only_text,
    share_of,
    summary_numbers,
    summary_text,
)
from hairline.tokens import load_tokens

if TYPE_CHECKING:
    from hairline.study.model import Study

def subsets(study: Study) -> list[tuple[str, pd.DataFrame]]:
    """Each group's rows, then all rows as Overall; without a group only Overall."""
    if not study.group:
        return [(study.overall, study.data)]
    labels = study.data[study.group].map(lambda value: None if pd.isna(value) else level_text(value))
    return [(name, study.data[labels == name]) for name in study.groups] + [(study.overall, study.data)]


def group_role(study: Study) -> dict[str, str]:
    return {"group": study.group} if study.group else {}


def counted_rows(study: Study, columns: dict[str, str], in_overall: bool = False) -> dict:
    """Rows in the study, analysed, and missing: each role in turn (variable, group, date) counts the rows still in
    that lack it. With a group, other_groups counts rows in groups that order leaves out; with `in_overall` those and
    the rows without a group still count as analysed, in Overall."""
    data, kept, missing = study.data, pd.Series(True, index=study.data.index), {}
    for role, column in columns.items():
        absent = is_missing(data[column])
        missing[role] = int((kept & absent).sum())
        kept &= ~absent
    found = {"total": len(data), "analysed": 0, "missing": missing}
    if study.group:
        other = kept & ~data[study.group].map(level_text).isin(study.groups)
        found["other_groups"] = int(other.sum())
        kept &= ~other
    overall = missing.get("group", 0) + found.get("other_groups", 0) if in_overall else 0
    found["analysed"] = int(kept.sum()) + overall
    return found


def numeric_rows(study: Study, name: str, parts: list, stats: Sequence[str]) -> tuple[list[list[str]], dict, dict]:
    digits, whole = digits_for(numbers(study.data[name])), is_whole(numbers(study.data[name]))
    found = {label: summary_numbers(numbers(rows_[name]), tuple(stats), int(is_missing(rows_[name]).sum()))
             for label, rows_ in parts}
    rows = [[f"{study.label_unit(name)}, {STAT_LABELS[stat]}",
             *[summary_text(found[label], stat, digits, whole) for label, _ in parts]] for stat in stats]
    return rows, {name: dict(zip(found, rows[0][1:], strict=True))}, found


def level_numbers(column: pd.Series, names: list[str]) -> dict:
    """n and missing, then the count and share (of the non-missing values) of each level."""
    present = column[~is_missing(column)].map(level_text)
    counts = {level: int((present == level).sum()) for level in names}
    return {"n": len(present), "missing": len(column) - len(present), "counts": counts,
            "shares": {level: share_of(count, len(present)) for level, count in counts.items()}}


def categorical_rows(study: Study, name: str, parts: list) -> tuple[list[list[str]], dict, dict]:
    names = levels(study.data[name])
    found = {label: level_numbers(subset[name], names) for label, subset in parts}
    rows = [[f"{study.label(name)}, n (%)", *([""] * len(parts))]]
    rows += [[f"  {level}", *[count_share(found[label]["counts"][level], found[label]["n"]) for label in found]]
             for level in names]
    values = {label: {level: row[1 + index] for level, row in zip(names, rows[1:], strict=True)}
              for index, label in enumerate(found)}
    return rows, {name: values}, found


def describe(study: Study, stats: Sequence[str] = ("median_iqr",), size: str = "double") -> Result:
    stats = (stats,) if isinstance(stats, str) else tuple(stats)
    check_stats(stats)
    study.require([study.group, *study.variables], "describe")
    study.require_one_row("describe")
    parts = subsets(study)
    found: dict = {"rows": counted_rows(study, group_role(study), in_overall=True),
                   "n": {label: len(rows) for label, rows in parts}, "variables": {}}
    counts = [format_number(count, 0) for count in found["n"].values()]
    table, values = [["n", *counts]], {"n": dict(zip(found["n"], counts, strict=True))}
    for name in study.variables:
        rows, shown, found["variables"][name] = (numeric_rows(study, name, parts, stats)
                                                 if study.types[name] == "numeric" else
                                                 categorical_rows(study, name, parts))
        table += rows
        values.update(shown)
    frame = pd.DataFrame(table, columns=["Characteristic", *[label for label, _ in parts]])
    text = (counts_text(study, parts, counts, found["n"][study.overall]) + overall_only_text(found["rows"])
            + missing_text(study, found))
    names = [label for label, _ in parts[:-1]]
    return Result(figure_for("describe", names, "groups", lambda: overview(study, parts, size)), frame, values, text,
                  found)


def counts_text(study: Study, parts: list, counts: list[str], total_rows: int) -> str:
    total = counted_text(total_rows, study.nouns)
    if not study.group:
        return f"{total}."
    groups = [f"{count} in {label}" for (label, _), count in zip(parts[:-1], counts[:-1], strict=True)]
    return f"{total}: {listed(groups)}."


def missing_text(study: Study, found: dict) -> str:
    """' Left out where missing: Age 1 and SOFA 2.'; empty when no variable misses a value."""
    missing = {name: found["variables"][name][study.overall]["missing"] for name in study.variables}
    parts = [f"{study.label(name)} {format_number(count, 0)}" for name, count in missing.items() if count]
    return f" Left out where missing: {listed(parts)}." if parts else ""


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
    title = f"Characteristics by {study.in_sentence(study.group)}" if study.group else "Characteristics"
    rules = load_tokens()["study"]
    columns = min(len(numeric), rules["overview_columns"])
    rows = -(-len(numeric) // columns)
    height = rules["overview_frame_mm"] + rows * (rules["overview_panel_mm"] + len(shown) * rules["overview_row_mm"])
    result = figure(title, subtitle="Range, interquartile range and median", size=size, height_mm=height,
                    panels=len(numeric), layout="pair", columns=columns)
    # The strip is sized from its rows, not the 8 x base an axes chart keeps: each group row keeps its own least.
    result.min_plot = rows * len(shown) * rules["overview_min_row"]
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
