"""Kaplan–Meier curves: step curves with bands and censor ticks, medians in the panel header,
the number at risk under the x-axis aligned to its ticks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from hairline import entities
from hairline.charts.common import check_columns
from hairline.charts.timeseries import groups_of, reference_style
from hairline.figure import HairlineFigure, figure
from hairline.numbers import format_number, format_p
from hairline.settings import current_settings
from hairline.stats.survival import km_estimate, km_median
from hairline.stats.tests import logrank
from hairline.ticks import nice_breaks
from hairline.tokens import load_tokens


def at_risk_from(table: pd.DataFrame, total: int, moments: Sequence[float]) -> list[int]:
    """Number at risk at each moment from an estimate table: the count at the next distinct time, 0 past the end."""
    counts = []
    for moment in moments:
        later = table[table["time"] >= moment]
        counts.append(int(later["at_risk"].iloc[0]) if len(later) else 0)
    return counts if len(table) else [total] * len(moments)


def draw_curve(ax, table: pd.DataFrame, color: str, label: str) -> None:
    rules, base = load_tokens()["survival"], current_settings().base_size
    width = load_tokens()["lines"]["data"] * base
    times = np.concatenate([[0.0], table["time"].to_numpy()])
    survival = np.concatenate([[1.0], table["survival"].to_numpy()])
    banded = table.dropna(subset=["low", "high"])
    ax.fill_between(np.concatenate([[0.0], banded["time"]]), np.concatenate([[1.0], banded["low"]]),
                    np.concatenate([[1.0], banded["high"]]), step="post", color=color, alpha=rules["band_opacity"],
                    linewidth=0, label="_nolegend_")
    ax.plot(times, survival, drawstyle="steps-post", color=color, linewidth=width, label=label)
    censored = table[table["censored"] > 0]
    ax.plot(censored["time"], censored["survival"], linestyle="none", marker="|", color=color,
            markersize=rules["censor_tick"] * base, markeredgewidth=rules["censor_width"] * base, label="_nolegend_")


def median_text(table: pd.DataFrame) -> str:
    median = km_median(table)
    return "not reached" if median is None else format_number(median, 1, current_settings().locale)


def header_stats(estimates: list[tuple[str, pd.DataFrame]], stats: Sequence[tuple[str, str]]) -> list[tuple[str, str]]:
    """One key number for the medians, in legend order ("9.1 vs 19.9"), then the user's statistics."""
    medians = " vs ".join(median_text(table) for _, table in estimates)
    return [("Median", medians)] + [(str(label), str(value)) for label, value in stats]


def fitter_table(fitter) -> tuple[pd.DataFrame, int]:
    """Estimate table and group size from a fitted Kaplan–Meier object (lifelines' KaplanMeierFitter: event_table,
    survival_function_, confidence_interval_); the fit keeps its own intervals."""
    for name in ("event_table", "survival_function_", "confidence_interval_"):
        if not hasattr(fitter, name):
            raise ValueError(f"hairline: kaplan_meier: a fit needs {name} (a fitted lifelines KaplanMeierFitter); "
                             f"got {type(fitter).__name__}")
    events = fitter.event_table
    rows = events[events["removed"] > 0]
    survival, bands = fitter.survival_function_.iloc[:, 0], fitter.confidence_interval_
    table = pd.DataFrame({"time": rows.index.to_numpy(dtype=float), "at_risk": rows["at_risk"].to_numpy(),
                          "events": rows["observed"].to_numpy(), "censored": rows["censored"].to_numpy(),
                          "survival": survival.loc[rows.index].to_numpy(),
                          "low": bands.iloc[:, 0].loc[rows.index].to_numpy(),
                          "high": bands.iloc[:, 1].loc[rows.index].to_numpy()})
    return table, int(events["entrance"].sum())


def estimates_from(data, time: str | None, event: str | None, by: str | None,
                   order: Sequence[str] | None) -> list[tuple[str, pd.DataFrame, int]]:
    """(name, estimate table, group size) per group: from raw rows, one fit, or a mapping of group to fit."""
    if isinstance(data, pd.DataFrame):
        check_columns(data, [time, event, by])
        return [(name, km_estimate(rows[time], rows[event]), len(rows)) for name, rows in groups_of(data, by, order)]
    fits = dict(data) if isinstance(data, Mapping) else {"": data}
    names = [str(name) for name in (order or fits)]
    return [(name, *fitter_table(fits[name])) for name in names]


def kaplan_meier(data, time: str | None = None, event: str | None = None, by: str | None = None, *,
                 title: str | None = None, subtitle: str | None = None, caption: str | None = None,
                 x_title: str = "Time", endpoint: str = "Survival", median_line: bool = True,
                 stats: Sequence[tuple[str, str]] = (), at_risk: bool = True, times: Sequence[float] | None = None,
                 order: Sequence[str] | None = None, test: bool = True, colors: Mapping[str, str] | None = None,
                 size: str = "onehalf") -> HairlineFigure:
    """Survival curves per group from time and event (1 = event, 0 = censored) columns, or from fitted
    Kaplan–Meier objects (one lifelines KaplanMeierFitter, or a mapping of group to one); with groups in raw data
    and `test`, the log-rank p joins the key numbers."""
    estimates = estimates_from(data, time, event, by, order)
    grouped = by is not None or len(estimates) > 1
    title = title or (f"{endpoint} by {str(by).replace('_', ' ')}" if by else endpoint)
    if by and test and isinstance(data, pd.DataFrame) and \
            not any(str(label).lower().startswith("log-rank") for label, _ in stats):
        test_result = logrank(data[time], data[event], [str(name) for name in data[by]])
        stats = [*stats, ("Log-rank", format_p(test_result["p"]))]
    result = figure(title, subtitle=subtitle, caption=caption, size=size)
    latest = max(float(table["time"].max()) for _, table, _ in estimates)
    moments = list(times) if times is not None else nice_breaks(0, latest)
    palette = entities.colors_for([name for name, _, _ in estimates], colors) if grouped else {}
    rows = []
    for name, table, total in estimates:
        color = palette.get(name, current_settings().palette[0])
        draw_curve(result.ax, table, color, name or endpoint)
        rows.append((name or endpoint, color, [(moment, format_number(count, 0)) for moment, count in
                                               zip(moments, at_risk_from(table, total, moments), strict=True)]))
    finish_survival(result, [(name, table) for name, table, _ in estimates], stats, endpoint, x_title,
                    median_line, grouped)
    if at_risk:
        result.table(rows, heading="Number at risk")
    return result


def finish_survival(result: HairlineFigure, estimates: list, stats, endpoint: str, x_title: str, median_line: bool,
                    grouped: bool) -> None:
    result.ax.update_datalim([(0.0, 0.0), (0.0, 1.0)])
    if median_line:
        dash = (0, tuple(load_tokens()["survival"]["median_dash"]))
        result.ax.axhline(0.5, **{**reference_style(), "linestyle": dash})
    result.percent_axis(0)
    result.x_title(x_title)
    result.panel_header(0, endpoint, stats=header_stats(estimates, stats))
    if grouped:
        result.legend()
