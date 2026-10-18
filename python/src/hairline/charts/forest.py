"""Forest plot: a results table with intervals, weighted squares and a pooled diamond."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from hairline.charts.common import check_columns, humanise
from hairline.charts.forest_geometry import forest_drawing, log_breaks
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.marks import lone_color
from hairline.numbers import format_interval, format_number, format_percent
from hairline.settings import current_settings
from hairline.ticks import axis_limits, nice_breaks
from hairline.tokens import load_tokens


def decimals(values: Sequence[float]) -> int:
    return next((digits for digits in range(4) if all(abs(round(value, digits) - value) < 1e-9 for value in values)), 3)


def forest_axis(lows: list[float], highs: list[float], ratio: bool, locale: str, null: float | None) -> dict:
    """Breaks covering every interval and the null line: 1-2-5 on a log scale for ratios (each label with its own
    decimals: 0.2, 0.5, 1, 2), nice breaks with shared decimals otherwise."""
    anchors = [] if null is None else [null]
    low, high = min(lows + anchors), max(highs + anchors)
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


def effect_text(estimate: float, low: float, high: float, interval: bool, digits: int, locale: str) -> str:
    return format_interval(estimate, low, high, digits, locale) if interval else format_number(estimate, digits, locale)


def forest_rows(data: pd.DataFrame, names: tuple[str, str, str, str], weight: str | None,
                columns: Mapping[str, str], digits: int, locale: str, interval: bool = True) -> list[dict]:
    study, estimate, low, high = names
    total = float(data[weight].sum()) if weight else None
    return [{"study": str(row[study]), "estimate": float(row[estimate]), "low": float(row[low]),
             "high": float(row[high]), "weight": float(row[weight]) if weight else None,
             "cells": [str(row[column]) for column in columns.values()],
             "effect_text": effect_text(row[estimate], row[low], row[high], interval, digits, locale),
             "weight_text": format_percent(row[weight] / total, 1, locale) if weight else None}
            for _, row in data.iterrows()]


def forest_spec(data: pd.DataFrame, study: str, estimate: str, low: str, high: str, *, weight: str | None = None,
                columns: Mapping[str, str] | None = None, pooled: Mapping | None = None, ratio: bool = True,
                favours: Sequence[str] | None = None, color: str, study_heading: str = "Study",
                effect_heading: str = "Effect [95 % CI]", weight_heading: str = "Weight", digits: int = 2,
                marker: str = "square", interval: bool = True, null: float | None | str = "auto") -> dict:
    """Everything the geometry needs, with numbers already formatted for the active locale."""
    columns = dict(columns or {})
    check_columns(data, [study, estimate, low, high, weight, *columns.values()])
    check_rows(data, study, low, high, ratio)
    locale = current_settings().locale
    rows = forest_rows(data, (study, estimate, low, high), weight, columns, digits, locale, interval)
    pooled_spec = None if pooled is None else {
        "label": pooled.get("label", "Pooled"), "estimate": pooled["estimate"], "low": pooled["low"],
        "high": pooled["high"], "effect_text": format_interval(pooled["estimate"], pooled["low"], pooled["high"],
                                                                digits, locale)}
    extra = [pooled_spec] if pooled_spec else []
    null = (1 if ratio else 0) if null == "auto" else null
    axis = forest_axis([row["low"] for row in rows + extra], [row["high"] for row in rows + extra], ratio, locale, null)
    return {"rows": rows, "columns": list(columns), "pooled": pooled_spec, "ratio": ratio, "null": null,
            "favours": list(favours) if favours else None, "axis": axis, "color": color, "study_heading": study_heading,
            "effect_heading": effect_heading, "weight_heading": weight_heading if weight else None, "marker": marker}


def model_table(model, exponentiate: bool) -> pd.DataFrame:
    """Terms, estimates and 95 % intervals of a fitted model (statsmodels-like: params and conf_int())."""
    limits = model.conf_int()
    table = pd.DataFrame({"term": [str(name) for name in model.params.index], "estimate": list(model.params),
                          "low": list(limits.iloc[:, 0]), "high": list(limits.iloc[:, 1])})
    table = table[~table["term"].str.lower().isin(["intercept", "const", "(intercept)"])]
    if exponentiate:
        table[["estimate", "low", "high"]] = np.exp(table[["estimate", "low", "high"]])
    return table


def forest(data, study: str = "study", estimate: str = "estimate", low: str = "low", high: str = "high", *,
           title: str | None = None, subtitle: str | None = None, caption: str | None = None,
           heterogeneity: str | None = None, exponentiate: bool = False, size: str = "onehalf",
           **options) -> HairlineFigure:
    """Forest plot from a results table or a fitted model (its terms, without the intercept); `exponentiate`
    turns log odds or log hazards into ratios. `options` as for forest_spec (weight, columns, pooled, favours…)."""
    if hasattr(data, "params") and hasattr(data, "conf_int"):
        data, study, estimate, low, high = model_table(data, exponentiate), "term", "estimate", "low", "high"
        options.setdefault("ratio", exponentiate)
    elif not {study, estimate, low, high} <= set(getattr(data, "columns", [])):
        raise ValueError(f"hairline: forest needs the study, estimate, low and high columns ({study}, {estimate}, "
                         f"{low}, {high}); columns: {', '.join(map(str, getattr(data, 'columns', [])))}")
    title = title or f"Effects by {humanise(study).lower()}"
    spec = forest_spec(data, study, estimate, low, high, color=lone_color(), **options)
    note = ". ".join(part.rstrip(".") for part in (heterogeneity, caption) if part)
    result = figure(title, subtitle=subtitle, caption=note + "." if note else None, size=size)
    result.draw(0, lambda box, measure, style: forest_drawing(spec, box, measure, style))
    return fit_height(result)
