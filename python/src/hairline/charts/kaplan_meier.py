"""Kaplan–Meier curves: step curves with bands and censor ticks, medians in the panel header,
the number at risk under the x-axis aligned to its ticks."""

from __future__ import annotations

import math
import numbers
from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from hairline import entities
from hairline.charts.common import check_columns, check_numeric
from hairline.charts.timeseries import groups_of, reference_style
from hairline.drawing import keep_plot_height
from hairline.figure import HairlineFigure, figure
from hairline.marks import lone_color
from hairline.numbers import auto_digits, format_number, format_p
from hairline.settings import current_settings
from hairline.stats.survival import km_estimate, km_median, median_digits
from hairline.stats.tests import logrank
from hairline.ticks import nice_breaks
from hairline.tokens import load_tokens


def at_risk_from(table: pd.DataFrame, total: float, moments: Sequence[float]) -> list[float]:
    """Number at risk at each moment: the count at the next distinct time, 0 past the end. A fit with delayed entry
    (its entries in table.attrs["entries"]) counts those who entered before the moment and have not yet left, so
    someone entering later is not yet at risk. Weighted fits keep their fractional counts."""
    entries = table.attrs.get("entries")
    if entries is not None:
        removed = table["events"] + table["censored"]
        return [float(sum(count for time, count in entries if time < moment or time <= 0)
                      - removed[table["time"] < moment].sum()) for moment in moments]
    counts = []
    for moment in moments:
        later = table[table["time"] >= moment]
        counts.append(float(later["at_risk"].iloc[0]) if len(later) else 0.0)
    return counts if len(table) else [float(total)] * len(moments)


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


def median_text(table: pd.DataFrame, digits: int = 1) -> str:
    median = km_median(table)
    return "not reached" if median is None else format_number(median, digits, current_settings().locale)


def header_stats(estimates: list[tuple[str, pd.DataFrame]], stats: Sequence[tuple[str, str]]) -> list[tuple[str, str]]:
    """One key number for the medians, in legend order ("9.1 vs 19.9"), then the user's statistics."""
    digits = median_digits([table for _, table in estimates])
    medians = " vs ".join(median_text(table, digits) for _, table in estimates)
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
    entered = events[events["entrance"] > 0]["entrance"]
    if (entered.index > entered.index.min()).any():
        table.attrs["entries"] = [(float(time), float(count)) for time, count in entered.items()]
    return table, float(events["entrance"].sum())


def check_rows(data: pd.DataFrame, time: str | None, event: str | None, by: str | None) -> None:
    """Raw rows name their time and event columns; times are finite numbers, events numbers or TRUE/FALSE."""
    if time is None or event is None:
        raise ValueError("hairline: kaplan_meier: name the time and event columns (time=..., event=...), or pass "
                         "fitted Kaplan–Meier objects")
    check_columns(data, [time, event, by])
    check_numeric(data, [time], "kaplan_meier")
    if not pd.api.types.is_numeric_dtype(data[event]):
        raise ValueError(f"hairline: kaplan_meier: '{event}' holds {data[event].dtype} values; code events as 1 "
                         "(event) and 0 (censored)")


def check_options(stats: Sequence, times: Sequence[float] | None) -> None:
    """Key numbers are (label, value) pairs; at-risk times are finite and not negative."""
    for item in stats:
        if isinstance(item, str) or not isinstance(item, Sequence) or len(item) != 2:
            raise ValueError(f"hairline: kaplan_meier: stats are (label, value) pairs such as ('HR', '0.72'); got "
                             f"{item!r}")
    for moment in times or ():
        if not isinstance(moment, numbers.Real) or not math.isfinite(moment) or moment < 0:
            raise ValueError(f"hairline: kaplan_meier: times are moments of 0 or more for the numbers at risk; got "
                             f"{moment!r}")


def estimates_from(data, time: str | None, event: str | None, by: str | None,
                   order: Sequence[str] | None) -> list[tuple[str, pd.DataFrame, int]]:
    """(name, estimate table, group size) per group: from raw rows, one fit, or a mapping of group to fit."""
    if isinstance(data, pd.DataFrame):
        check_rows(data, time, event, by)
        return [(name, km_estimate(rows[time], rows[event]), len(rows))
                for name, rows in groups_of(data, by, order, "kaplan_meier")]
    fits = {str(name): fit for name, fit in (data.items() if isinstance(data, Mapping) else {"": data}.items())}
    names = [str(name) for name in (order or fits)]
    unknown = [name for name in names if name not in fits]
    if unknown:
        raise ValueError(f"hairline: kaplan_meier: order names '{unknown[0]}', which has no fit; fits are given for "
                         f"{', '.join(fits)}")
    return [(name, *fitter_table(fits[name])) for name in names]


def logrank_stats(data: pd.DataFrame, time: str, event: str, by: str, order: Sequence[str] | None) -> list:
    """The log-rank p over the groups the chart draws (those in `order`, when given); none without events."""
    shown = pd.concat([rows for _, rows in groups_of(data, by, order, "kaplan_meier")]) if order else data
    result = logrank(shown[time], shown[event], [str(name) for name in shown[by]])
    return [] if math.isnan(result["p"]) else [("Log-rank", format_p(result["p"]))]


def kaplan_meier(data, time: str | None = None, event: str | None = None, by: str | None = None, *,
                 title: str | None = None, subtitle: str | None = None, caption: str | None = None,
                 x_title: str = "Time", endpoint: str = "Survival", median_line: bool = True,
                 stats: Sequence[tuple[str, str]] = (), at_risk: bool = True, times: Sequence[float] | None = None,
                 order: Sequence[str] | None = None, test: bool = True, colors: Mapping[str, str] | None = None,
                 size: str = "onehalf") -> HairlineFigure:
    """Survival curves per group from time and event (1 = event, 0 = censored) columns, or from fitted
    Kaplan–Meier objects (one lifelines KaplanMeierFitter, or a mapping of group to one); with groups in raw data
    and `test`, the log-rank p joins the key numbers. A figure whose frame would leave the curves less than 8 x the
    base size high (a narrow figure with a number-at-risk table) grows taller."""
    check_options(stats, times)
    estimates = estimates_from(data, time, event, by, order)
    if not estimates:
        raise ValueError("hairline: kaplan_meier: no rows to draw")
    grouped = by is not None or len(estimates) > 1
    title = title or (f"{endpoint} by {str(by).replace('_', ' ')}" if by else endpoint)
    if by and test and isinstance(data, pd.DataFrame) and \
            not any(str(label).lower().startswith("log-rank") for label, _ in stats):
        stats = [*stats, *logrank_stats(data, time, event, by, order)]
    result = figure(title, subtitle=subtitle, caption=caption, size=size)
    latest = max(float(table["time"].max()) for _, table, _ in estimates)
    moments = sorted(set(times)) if times is not None else nice_breaks(0, latest)
    palette = entities.colors_for([name for name, _, _ in estimates], colors) if grouped else {}
    rows = []
    for name, table, total in estimates:
        color = palette.get(name, lone_color())
        draw_curve(result.ax, table, color, name or endpoint)
        counts = at_risk_from(table, total, moments)
        digits = auto_digits(counts)
        rows.append((name or endpoint, color, [(moment, format_number(count, digits)) for moment, count in
                                               zip(moments, counts, strict=True)]))
    finish_survival(result, [(name, table) for name, table, _ in estimates], stats, endpoint, x_title,
                    median_line, grouped)
    if at_risk:
        result.table(rows, heading="Number at risk")
    # A narrow figure (one column of a two-column page) grows taller rather than squeezing the curves away.
    return keep_plot_height(result, load_tokens()["survival"]["min_plot"] * result.settings.base_size)


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
