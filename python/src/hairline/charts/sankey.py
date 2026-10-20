"""Sankey: flows through two or more columns, links coloured by the group of one column."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

from hairline import entities
from hairline.charts.common import check_columns, check_labels, humanise, joined, with_counts
from hairline.charts.sankey_geometry import sankey_drawing
from hairline.figure import HairlineFigure, figure
from hairline.numbers import auto_digits, format_number
from hairline.settings import current_settings


def check_paths(data: pd.DataFrame, columns: list[str], value: str) -> None:
    if len(columns) < 2:
        raise ValueError(f"hairline: sankey needs at least two columns; got {', '.join(columns) or 'none'}")
    for _, row in data.iterrows():
        if pd.notna(row[value]) and row[value] < 0:
            raise ValueError(f"hairline: sankey: {' → '.join(str(row[column]) for column in columns)} has a negative "
                             f"value ({row[value]}); flows need values of zero or more")


def aggregate_links(data: pd.DataFrame, columns: list[str], value: str, group: str | None) -> list[dict]:
    """One link per column pair, source, target and colour group, in order of first appearance."""
    totals: dict[tuple, float] = {}
    for _, row in data[data[value].notna()].iterrows():
        for index in range(len(columns) - 1):
            key = (index, str(row[columns[index]]), str(row[columns[index + 1]]), str(row[group]) if group else "")
            totals[key] = totals.get(key, 0.0) + float(row[value])
    return [{"column": index, "source": source, "target": target, "group": key_group, "value": amount}
            for (index, source, target, key_group), amount in totals.items() if amount > 0]


def column_nodes(data: pd.DataFrame, columns: list[str], links: list[dict], color_column: int | None,
                 palette: Mapping[str, str], digits: int = 0) -> list:
    settings, nodes = current_settings(), []
    for index, column in enumerate(columns):
        names = list(dict.fromkeys(str(name) for name in data[column]))
        column_nodes = []
        for name in names:
            incoming = sum(link["value"] for link in links if link["column"] == index - 1 and link["target"] == name)
            outgoing = sum(link["value"] for link in links if link["column"] == index and link["source"] == name)
            amount = max(incoming, outgoing)
            if amount > 0:
                color = palette.get(name, settings.neutral["muted"]) if index == color_column else \
                    settings.neutral["muted"]
                column_nodes.append({"name": name, "value": amount, "value_text": format_number(amount, digits),
                                     "color": color})
        nodes.append(column_nodes)
    return nodes


def sankey_spec(data: pd.DataFrame, columns: Sequence[str], value: str, *, color_by: str | None = None,
                headings: Sequence[str] | None = None, colors: Mapping[str, str] | None = None) -> dict:
    """Nodes per column and links with colours and formatted values, ready for the geometry."""
    columns = list(columns)
    check_columns(data, columns + [value])
    group = None if color_by == "none" else (color_by or columns[-1])
    if group is not None:
        check_columns(data, [group])
    check_labels(data, columns + [group], "sankey")
    check_paths(data, columns, value)
    if headings is not None and len(headings) != len(columns):
        raise ValueError(f"hairline: sankey: {len(headings)} heading(s) for {len(columns)} columns; give one per "
                         f"column")
    links = aggregate_links(data, columns, value, group)
    if not links:
        raise ValueError(f"hairline: sankey: no flows above zero to draw in '{value}'")
    digits = auto_digits([link["value"] for link in links])
    color_column = columns.index(group) if group in columns else None
    groups = list(dict.fromkeys(link["group"] for link in links))
    palette = entities.colors_for(groups, colors) if group else {}
    nodes = column_nodes(data, columns, links, color_column, palette, digits)
    faint = current_settings().neutral["faint"]
    for link in links:
        link["color"] = palette[link["group"]] if group else faint
    groups = list(dict.fromkeys(link["group"] for link in links))
    return {"headings": list(headings) if headings else columns, "nodes": nodes, "links": links, "groups": groups}


def sankey(data: pd.DataFrame, columns: Sequence[str], value: str | None = None, *, title: str | None = None,
           subtitle: str | None = None,
           caption: str | None = None, color_by: str | None = None, headings: Sequence[str] | None = None,
           colors: Mapping[str, str] | None = None, size: str = "onehalf") -> HairlineFigure:
    """Flows from left to right through `columns`; links take the colour of their group in `color_by`."""
    data, value = with_counts(data, value)
    title = title or f"{humanise(value)} from {joined(columns[:1])} to {joined(columns[-1:])}"
    spec = sankey_spec(data, columns, value, color_by=color_by,
                       headings=headings or [humanise(column) for column in columns], colors=colors)
    result = figure(title, subtitle=subtitle, caption=caption, size=size)
    result.draw(0, lambda box, measure, style: sankey_drawing(spec, box, measure, style))
    return result
