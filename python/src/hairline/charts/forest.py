"""Forest plot: a results table with intervals, weighted squares and a pooled diamond."""

from __future__ import annotations

import math
import numbers
import warnings
from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from hairline.charts.common import check_columns, humanise
from hairline.charts.forest_geometry import forest_drawing, log_breaks
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.marks import lone_color
from hairline.numbers import auto_digits, format_interval, format_number, format_percent
from hairline.settings import current_settings
from hairline.ticks import axis_limits, nice_breaks
from hairline.tokens import load_tokens


def decimals(values: Sequence[float]) -> int:
    """The fewest decimals that show every value exactly (axis breaks: 0.2, 0.0005), up to study.max_digits."""
    most = load_tokens()["study"]["max_digits"]
    return next((digits for digits in range(most + 1)
                 if all(abs(round(value, digits) - value) < 1e-12 for value in values)), most)


def default_digits(data: pd.DataFrame, columns: Sequence[str]) -> int:
    """Two decimals, or more where the estimates and limits are small or close together (0.0004 [0.0003; 0.0005])."""
    return max(2, auto_digits(data[list(columns)].to_numpy(dtype=float).ravel()))


def forest_axis(lows: list[float], highs: list[float], ratio: bool, locale: str, null: float | None) -> dict:
    """Breaks covering every interval and the null line: 1-2-5 on a log scale for ratios (each label with its own
    decimals: 0.2, 0.5, 1, 2), nice breaks with shared decimals otherwise."""
    anchors = [] if null is None else [null]
    low, high = min(lows + anchors), max(highs + anchors)
    if low == high:  # every value alike: an axis around it, a factor of two for ratios
        low, high = (low / 2, high * 2) if ratio else (low - (abs(low) or 1), high + (abs(high) or 1))
    breaks = log_breaks(low, high, load_tokens()["forest"]["max_ticks"]) if ratio else nice_breaks(low, high)
    limits = (breaks[0], breaks[-1]) if ratio else axis_limits(low, high, breaks)
    shared = decimals(breaks)
    labels = [format_number(value, decimals([value]) if ratio else shared, locale) for value in breaks]
    return {"breaks": breaks, "labels": labels,
            "low": limits[0], "high": limits[1]}


def check_interval(name: str, estimate: float, low: float, high: float, ratio: bool) -> None:
    """Present, ordered limits around their estimate, above zero on a ratio scale."""
    values = (estimate, low, high)
    if not all(isinstance(value, numbers.Real) and math.isfinite(value) for value in values):
        raise ValueError(f"hairline: forest: {name!r} has estimate {estimate}, low {low} and high {high}; all three "
                         f"must be numbers")
    if low > high:
        raise ValueError(f"hairline: forest: {name!r} has a lower limit above its upper limit")
    if not low <= estimate <= high:
        raise ValueError(f"hairline: forest: {name!r} has its estimate {estimate:g} outside its interval "
                         f"[{low:g}; {high:g}]")
    if ratio and low <= 0:
        raise ValueError(f"hairline: forest: {name!r} has a limit of 0 or below on a ratio scale; "
                         "pass ratio=False for differences")


def check_rows(data: pd.DataFrame, names: tuple[str, str, str, str], weight: str | None, ratio: bool) -> None:
    study, estimate, low, high = names
    if not len(data):
        raise ValueError("hairline: forest: no rows to draw")
    for _, row in data.iterrows():
        check_interval(str(row[study]), row[estimate], row[low], row[high], ratio)
    if weight:
        weights = data[weight].astype(float)
        if not (np.isfinite(weights) & (weights >= 0)).all() or not weights.sum() > 0:
            raise ValueError(f"hairline: forest: '{weight}' must hold weights of 0 or more that add up to more than "
                             f"0; got {', '.join(f'{value:g}' for value in weights)}")


def checked_pooled(pooled: Mapping, ratio: bool) -> Mapping:
    missing = [key for key in ("estimate", "low", "high") if key not in pooled]
    if missing:
        raise ValueError(f"hairline: forest: pooled needs estimate, low and high; missing {', '.join(missing)}")
    check_interval(str(pooled.get("label", "Pooled")), pooled["estimate"], pooled["low"], pooled["high"], ratio)
    return pooled


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
                effect_heading: str = "Effect [95 % CI]", weight_heading: str = "Weight", digits: int | None = None,
                marker: str = "square", interval: bool = True, null: float | None | str = "auto") -> dict:
    """Everything the geometry needs, with numbers already formatted for the active locale."""
    columns = dict(columns or {})
    check_columns(data, [study, estimate, low, high, weight, *columns.values()])
    check_rows(data, (study, estimate, low, high), weight, ratio)
    if favours is not None and len(favours) != 2:
        raise ValueError(f"hairline: forest: favours takes two labels (left, right); got {len(favours)}")
    pooled = None if pooled is None else checked_pooled(pooled, ratio)
    digits = default_digits(data, [estimate, low, high]) if digits is None else digits
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


def model_terms(model, count: int) -> list[str]:
    """Term names: the params' index, else the model's exog_names, else x1, x2, ... as statsmodels numbers them."""
    index = getattr(model.params, "index", None)
    names = list(index) if index is not None else getattr(getattr(model, "model", None), "exog_names", None)
    return [str(name) for name in names] if names is not None and len(names) == count else \
        [f"x{number}" for number in range(1, count + 1)]


def model_table(model, exponentiate: bool) -> pd.DataFrame:
    """Terms, estimates and 95 % intervals of a fitted model (statsmodels-like: params and conf_int()), whether it
    was fitted from pandas objects (named terms) or arrays (names from the model's exog_names)."""
    estimates, limits = np.asarray(model.params, dtype=float), np.asarray(model.conf_int(), dtype=float)
    table = pd.DataFrame({"term": model_terms(model, len(estimates)), "estimate": estimates,
                          "low": limits[:, 0], "high": limits[:, 1]})
    table = table[~table["term"].str.lower().isin(["intercept", "const", "(intercept)"])]
    aliased = table[table[["estimate", "low", "high"]].isna().any(axis=1)]
    if len(aliased):
        warnings.warn(f"hairline: terms without an estimate (aliased with others) are left out: "
                      f"{', '.join(aliased['term'])}", UserWarning, stacklevel=3)
        table = table.drop(aliased.index)
    if not len(table):
        raise ValueError("hairline: the model has no terms with an estimate besides the intercept")
    if exponentiate:
        table[["estimate", "low", "high"]] = np.exp(table[["estimate", "low", "high"]])
    return table


def ratio_model(model) -> bool:
    """Log-odds and log-rate models (logistic, Poisson, Cox) are read as ratios, as R does for glm and coxph."""
    inner = getattr(model, "model", None)
    link = type(getattr(getattr(inner, "family", None), "link", None)).__name__.lower()
    names = {type(inner).__name__, type(model).__name__}
    return link in ("logit", "log") or bool(names & {"Logit", "Poisson", "NegativeBinomial", "PHReg"})


def forest(data, study: str = "study", estimate: str = "estimate", low: str = "low", high: str = "high", *,
           weight: str | None = None, columns: Mapping[str, str] | None = None, pooled: Mapping | None = None,
           ratio: bool = True, favours: Sequence[str] | None = None, heterogeneity: str | None = None,
           title: str | None = None, subtitle: str | None = None, caption: str | None = None,
           exponentiate: bool | None = None, size: str = "onehalf", **options) -> HairlineFigure:
    """Forest plot from a results table or a fitted model (its terms, without the intercept). For a model,
    `exponentiate` (default: on for logistic, Poisson and Cox models) turns log odds or log hazards into ratios.
    `options` as for forest_spec (study_heading, effect_heading, digits, marker, null). On a figure too narrow for
    the columns beside the intervals (one column of a two-column page), they sit on a line under each study."""
    if hasattr(data, "params") and hasattr(data, "conf_int"):
        exponentiate = ratio_model(data) if exponentiate is None else exponentiate
        data, study, estimate, low, high = model_table(data, exponentiate), "term", "estimate", "low", "high"
        ratio = exponentiate
    elif not {study, estimate, low, high} <= set(getattr(data, "columns", [])):
        raise ValueError(f"hairline: forest needs the study, estimate, low and high columns ({study}, {estimate}, "
                         f"{low}, {high}); columns: {', '.join(map(str, getattr(data, 'columns', [])))}")
    title = title or f"Effects by {humanise(study).lower()}"
    spec = forest_spec(data, study, estimate, low, high, weight=weight, columns=columns, pooled=pooled, ratio=ratio,
                       favours=favours, color=lone_color(), **options)
    note = ". ".join(part.rstrip(".") for part in (heterogeneity, caption) if part)
    result = figure(title, subtitle=subtitle, caption=note + "." if note else None, size=size)
    result.draw(0, lambda box, measure, style: forest_drawing(spec, box, measure, style))
    return fit_height(result)
