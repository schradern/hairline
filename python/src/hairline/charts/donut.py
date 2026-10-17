"""Donut and nested donut: one ring, or up to three hierarchy levels."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from hairline import entities
from hairline.charts.common import check_columns, fold_other
from hairline.charts.donut_geometry import donut_drawing
from hairline.color.tints import tints
from hairline.figure import HairlineFigure, figure
from hairline.numbers import format_number, format_percent
from hairline.settings import current_settings
from hairline.tokens import load_tokens

LABEL_MODES = ("outside", "key", "ring")


def totals(data: pd.DataFrame, columns: list[str], value: str) -> pd.DataFrame:
    """Sum of `value` per combination of `columns`, in order of first appearance."""
    grouped = data.groupby(columns, sort=False, dropna=False)[value].sum().reset_index()
    for _, row in grouped.iterrows():
        if row[value] < 0:
            raise ValueError(f"hairline: donut: {' / '.join(map(str, row[columns]))!r} has a negative value "
                             f"({row[value]}); shares need values of zero or more")
    return grouped[grouped[value] > 0]


def segment(name: str, amount: float, total: float, color: str, parent: int | None, index: int) -> dict:
    share = amount / total
    return {"name": name, "value": float(amount), "share": share, "share_text": format_percent(share, 0),
            "color": color, "parent": parent, "index": index}


def top_ring(data: pd.DataFrame, column: str, value: str, fold: bool) -> list[dict]:
    """Top-level segments in entity colours; a folded "Other" slice is drawn in context grey."""
    grouped = totals(data, [column], value)
    names, amounts = [str(name) for name in grouped[column]], list(grouped[value])
    folded = fold and len(names) > load_tokens()["donut"]["max_slices"]
    if folded:
        names, amounts = fold_other(names, amounts, load_tokens()["donut"]["max_slices"])
    colors = [entities.color(name) for name in (names[:-1] if folded else names)]
    if folded:
        colors.append(load_tokens()["focus"]["context"])
    total = sum(amounts)
    return [segment(name, amount, total, color, None, index)
            for index, (name, amount, color) in enumerate(zip(names, amounts, colors, strict=True))]


def child_ring(data: pd.DataFrame, levels: list[str], value: str, parents: list[dict], total: float) -> list[dict]:
    grouped, ring = totals(data, levels, value), []
    for parent in parents:
        rows = grouped[grouped[levels[-2]].astype(str) == parent["name"]]
        colors = tints(parent["color"], len(rows))
        for color, (_, row) in zip(colors, rows.iterrows(), strict=True):
            ring.append(segment(str(row[levels[-1]]), row[value], total, color, parent["index"], len(ring)))
    return ring


def donut_rings(data: pd.DataFrame, label: str | None, value: str, levels: Sequence[str] | None) -> list[list[dict]]:
    """Segments per ring, inner to outer; children follow their parent's order and use its tints."""
    levels = list(levels) if levels else [label]
    check_columns(data, levels + [value])
    if len(levels) > load_tokens()["donut"]["max_levels"]:
        raise ValueError(f"hairline: donut: {len(levels)} levels given ({', '.join(levels)}); at most 3 levels fit")
    rings = [top_ring(data, levels[0], value, fold=len(levels) == 1)]
    total = sum(item["value"] for item in rings[0])
    for depth in range(1, len(levels)):
        rings.append(child_ring(data, levels[:depth + 1], value, rings[-1], total))
    return rings


def donut(data: pd.DataFrame, label: str | None, value: str, *, levels: Sequence[str] | None = None, title: str,
          subtitle: str | None = None, caption: str | None = None, labels: str | None = None, total: bool = True,
          total_label: str | None = None, size: str = "onehalf") -> HairlineFigure:
    """Donut with labels outside (one ring) or a hierarchical key (nested rings); `labels="ring"` labels the arcs."""
    rings = donut_rings(data, label, value, levels)
    mode = labels or ("outside" if len(rings) == 1 else "key")
    if mode not in LABEL_MODES or (mode == "outside" and len(rings) > 1):
        raise ValueError(f"hairline: donut: labels {mode!r} does not fit {len(rings)} ring(s); use "
                         f"{'outside, key or ring' if len(rings) == 1 else 'key or ring'}")
    amount = format_number(sum(item["value"] for item in rings[0]), 0, current_settings().locale)
    spec = {"rings": rings, "labels": mode, "total": amount if total else None, "total_label": total_label}
    result = figure(title, subtitle=subtitle, caption=caption, size=size)
    result.draw(0, lambda box, measure, style: donut_drawing(spec, box, measure, style))
    return result
