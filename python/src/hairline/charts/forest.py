"""Forest plot: a results table with intervals, weighted squares and a pooled diamond."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

from hairline.charts.common import check_columns
from hairline.charts.forest_geometry import forest_drawing, log_breaks
from hairline.figure import HairlineFigure, figure
from hairline.numbers import format_interval, format_number, format_percent
from hairline.settings import current_settings
from hairline.ticks import axis_limits, nice_breaks
from hairline.tokens import load_tokens


def decimals(values: Sequence[float]) -> int:
    return next((digits for digits in range(4) if all(abs(round(value, digits) - value) < 1e-9 for value in values)), 3)


def forest_axis(lows: list[float], highs: list[float], ratio: bool, locale: str) -> dict:
    """Breaks covering every interval and the null line: 1-2-5 on a log scale for ratios (each label with its own
    decimals: 0.2, 0.5, 1, 2), nice breaks with shared decimals otherwise."""
    null = 1.0 if ratio else 0.0
    low, high = min(lows + [null]), max(highs + [null])
    breaks = log_breaks(low, high, load_tokens()["forest"]["max_ticks"]) if ratio else nice_breaks(low, high)
    limits = (breaks[0], breaks[-1]) if ratio else axis_limits(low, high, breaks)
    shared = decimals(breaks)
    labels = [format_number(value, decimals([value]) if ratio else shared, locale) for value in breaks]
    return {"breaks": breaks, "labels": labels,
            "low": limits[0], "high": limits[1]}


def check_rows(data: pd.DataFrame, study: str, low: str, high: str, ratio: bool) -> None:
    for _, row in data.iterrows():
        if row[low] > row[high]:
            raise ValueError(f"hairline: forest: {row[study]!r} has a lower limit above its upper limit")
        if ratio and row[low] <= 0:
            raise ValueError(f"hairline: forest: {row[study]!r} has a limit of 0 or below on a ratio scale; "
                             "pass ratio=False for differences")


def forest_rows(data: pd.DataFrame, names: tuple[str, str, str, str], weight: str | None,
                columns: Mapping[str, str], digits: int, locale: str) -> list[dict]:
    study, estimate, low, high = names
    total = float(data[weight].sum()) if weight else None
    return [{"study": str(row[study]), "estimate": float(row[estimate]), "low": float(row[low]),
             "high": float(row[high]), "weight": float(row[weight]) if weight else None,
             "cells": [str(row[column]) for column in columns.values()],
             "effect_text": format_interval(row[estimate], row[low], row[high], digits, locale),
             "weight_text": format_percent(row[weight] / total, 1, locale) if weight else None}
            for _, row in data.iterrows()]


def forest_spec(data: pd.DataFrame, study: str, estimate: str, low: str, high: str, *, weight: str | None = None,
                columns: Mapping[str, str] | None = None, pooled: Mapping | None = None, ratio: bool = True,
                favours: Sequence[str] | None = None, color: str, study_heading: str = "Study",
                effect_heading: str = "Effect [95 % CI]", weight_heading: str = "Weight", digits: int = 2) -> dict:
    """Everything the geometry needs, with numbers already formatted for the active locale."""
    columns = dict(columns or {})
    check_columns(data, [study, estimate, low, high, weight, *columns.values()])
    check_rows(data, study, low, high, ratio)
    locale = current_settings().locale
    rows = forest_rows(data, (study, estimate, low, high), weight, columns, digits, locale)
    pooled_spec = None if pooled is None else {
        "label": pooled.get("label", "Pooled"), "estimate": pooled["estimate"], "low": pooled["low"],
        "high": pooled["high"], "effect_text": format_interval(pooled["estimate"], pooled["low"], pooled["high"],
                                                                digits, locale)}
    extra = [pooled_spec] if pooled_spec else []
    axis = forest_axis([row["low"] for row in rows + extra], [row["high"] for row in rows + extra], ratio, locale)
    return {"rows": rows, "columns": list(columns), "pooled": pooled_spec, "ratio": ratio, "null": 1 if ratio else 0,
            "favours": list(favours) if favours else None, "axis": axis, "color": color, "study_heading": study_heading,
            "effect_heading": effect_heading, "weight_heading": weight_heading if weight else None}


def forest(data: pd.DataFrame, study: str, estimate: str, low: str, high: str, *, title: str,
           subtitle: str | None = None, caption: str | None = None, heterogeneity: str | None = None,
           size: str = "onehalf", **options) -> HairlineFigure:
    """Forest plot from a results table; `options` as for forest_spec (weight, columns, pooled, ratio, favours…)."""
    spec = forest_spec(data, study, estimate, low, high, color=current_settings().palette[0], **options)
    note = ". ".join(part.rstrip(".") for part in (heterogeneity, caption) if part)
    result = figure(title, subtitle=subtitle, caption=note + "." if note else None, size=size)
    result.draw(0, lambda box, measure, style: forest_drawing(spec, box, measure, style))
    return result
