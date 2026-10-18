"""Funnel plot: effect against standard error, pseudo 95 % limits, Egger's test."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from hairline.charts.common import check_columns, humanise
from hairline.charts.forest import decimals
from hairline.charts.forest_geometry import log_breaks
from hairline.charts.funnel_geometry import funnel_drawing
from hairline.figure import HairlineFigure, figure
from hairline.marks import lone_color
from hairline.numbers import format_number, format_p
from hairline.settings import current_settings
from hairline.stats.tests import egger
from hairline.ticks import nice_breaks
from hairline.tokens import load_tokens


def funnel_axes(effects: np.ndarray, errors: np.ndarray, pooled: float, ratio: bool, locale: str) -> tuple[dict, dict]:
    reach = load_tokens()["funnel"]["z"] * float(errors.max())
    low = min(float(effects.min()), pooled - reach, 0.0)
    high = max(float(effects.max()), pooled + reach, 0.0)
    if ratio:
        breaks = log_breaks(math.exp(low), math.exp(high), load_tokens()["forest"]["max_ticks"])
        labels = [format_number(value, decimals([value]), locale) for value in breaks]
        x_axis = {"breaks": breaks, "labels": labels, "low": breaks[0], "high": breaks[-1]}
    else:
        breaks = nice_breaks(low, high)
        labels = [format_number(value, decimals(breaks), locale) for value in breaks]
        x_axis = {"breaks": breaks, "labels": labels, "low": min(low, breaks[0]), "high": max(high, breaks[-1])}
    y_breaks = nice_breaks(0.0, float(errors.max()))
    y_axis = {"breaks": y_breaks, "labels": [format_number(value, decimals(y_breaks), locale) for value in y_breaks],
              "high": max(y_breaks[-1], float(errors.max()))}
    return x_axis, y_axis


def funnel_spec(data: pd.DataFrame, estimate: str, se: str, *, ratio: bool = True, pooled: float | None = None,
                x_title: str | None = None) -> dict:
    """Points on the analysis scale (log for ratios), the pooled estimate (inverse-variance unless given) and axes."""
    check_columns(data, [estimate, se])
    effects = np.log(data[estimate].to_numpy(dtype=float)) if ratio else data[estimate].to_numpy(dtype=float)
    errors = data[se].to_numpy(dtype=float)
    weights = 1 / errors ** 2
    centre = float((weights * effects).sum() / weights.sum()) if pooled is None else (
        math.log(pooled) if ratio else pooled)
    x_axis, y_axis = funnel_axes(effects, errors, centre, ratio, current_settings().locale)
    return {"points": list(zip(effects.tolist(), errors.tolist(), strict=True)), "pooled": centre, "ratio": ratio,
            "null": 0.0, "x_axis": x_axis, "y_axis": y_axis, "x_title": x_title or humanise(estimate),
            "y_title": "Standard error", "color": lone_color(),
            "egger": egger(effects, errors)}


def funnel(data: pd.DataFrame, estimate: str, se: str, *, title: str | None = None, subtitle: str | None = None,
           caption: str | None = None, ratio: bool = True, pooled: float | None = None, x_title: str | None = None,
           size: str = "onehalf") -> HairlineFigure:
    """Funnel plot with the pooled estimate and Egger's test for small-study effects as key numbers."""
    spec = funnel_spec(data, estimate, se, ratio=ratio, pooled=pooled, x_title=x_title)
    locale = current_settings().locale
    result = figure(title or f"Funnel plot of {spec['x_title'].lower()}", subtitle=subtitle, caption=caption,
                    size=size)
    result.draw(0, lambda box, measure, style: funnel_drawing(spec, box, measure, style))
    value = math.exp(spec["pooled"]) if ratio else spec["pooled"]
    result.panel_header(0, "Pooled", stats=[("Estimate", format_number(value, 2, locale)),
                                            ("Egger", format_p(spec["egger"], locale))])
    return result
