"""Small-multiple time series with two levels of detail."""

from __future__ import annotations

import math
import numbers
from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from hairline.charts.common import (
    check_columns,
    check_labels,
    check_numeric,
    check_present,
    clip_caption,
    clip_limits,
    humanise,
    ordered_names,
    partial_caption,
    with_caption,
)
from hairline.charts.options import Reference, apply_options
from hairline.charts.summaries import STAT_NAMES, stat_label
from hairline.charts.timeseries_summary import (
    checked_summary,
    draw_summary_series,
    panel_stats,
    summary_legend_items,
)
from hairline.figure import HairlineFigure, figure
from hairline.focus import REFERENCE_ID
from hairline.fonts import families
from hairline.marks import SECONDARY_ID, lone_color
from hairline.numbers import format_number, format_percent
from hairline.settings import current_settings, role_size
from hairline.tokens import load_tokens


def groups_of(data: pd.DataFrame, by: str | None, order: Sequence[str] | None,
              chart: str = "chart") -> list[tuple[str, pd.DataFrame]]:
    """Rows per group in `order` (or category, else data order); groups match by their text, so order=["1"] finds
    the group 1. A missing group label and an order naming no group are refused."""
    if by is None:
        return [("", data)]
    check_labels(data, [by], chart)
    names = ordered_names(data[by], order, chart, by)
    labels = data[by].astype(str)
    return [(name, data[labels == name]) for name in names]


def formatter(percent: bool):
    return (lambda value, digits=1: format_percent(value, digits)) if percent else (
        lambda value, digits=1: format_number(value, digits))


def with_iso_dates(data: pd.DataFrame, x: str) -> pd.DataFrame:
    """ISO date text on x (2025-01-31, 2025-01-31T10:00) becomes dates, so the axis is a time axis, as over_time()
    reads it; other text stays as it is."""
    if pd.api.types.is_numeric_dtype(data[x]) or pd.api.types.is_datetime64_any_dtype(data[x]):
        return data
    parsed = iso_datetimes(data[x])
    return data.assign(**{x: parsed}) if parsed.notna().all() else data


def iso_datetimes(values: pd.Series) -> pd.Series:
    """ISO date and time text as datetimes, NaT where a value is not ISO. Text with zone offsets (+01:00 and +02:00
    across a clock change) is read in UTC, which mixed offsets need."""
    zoned = values.astype(str).str.contains(r"(?:Z|[+-]\d{2}:?\d{2})$", regex=True).any()
    return pd.to_datetime(values, format="ISO8601", errors="coerce", utc=bool(zoned))


def check_window(window: object) -> None:
    if isinstance(window, bool) or not isinstance(window, numbers.Real) or not window >= 1 or window != int(window):
        raise ValueError(f"hairline: timeseries: window must be a whole number of 1 or more; got {window!r}")


def draw_series(ax, rows: pd.DataFrame, x: str, y: str, color: str, window: int, raw: bool) -> None:
    lines, base = load_tokens()["lines"], current_settings().base_size
    rows = rows.sort_values(x)
    if raw:
        ax.plot(rows[x], rows[y], color=color, linewidth=lines["secondary"] * base, alpha=lines["secondary_opacity"],
                gid=SECONDARY_ID)
    smooth = rows[y].rolling(int(window), min_periods=1).mean()
    ax.plot(rows[x], smooth, color=color, linewidth=lines["data"] * base)


def reference_style() -> dict:
    rules, base = load_tokens()["reference"], current_settings().base_size
    return {"color": rules["color"], "linewidth": rules["width"] * base, "gid": REFERENCE_ID, "label": "_nolegend_"}


def caption_note(ax, text: str, x: object, settings) -> None:
    """Event label at the bottom of the panel, right of its line (the top holds thresholds and their labels)."""
    gap = load_tokens()["reference"]["label_gap"] * role_size(settings, "caption")
    ax.annotate(text, xy=(x, 0), xycoords=("data", "axes fraction"), xytext=(gap, gap), textcoords="offset points",
                ha="left", va="bottom", fontsize=role_size(settings, "caption"), color=settings.neutral["faint"],
                fontfamily=families(settings.font), annotation_clip=False)


def as_x(value: object, is_date: bool, key: str) -> object:
    """A band's or event's position on the x axis: a date (or ISO text) on a date axis, a number otherwise."""
    if not is_date:
        if isinstance(value, bool) or not isinstance(value, numbers.Real) or not math.isfinite(value):
            raise ValueError(f"hairline: timeseries: {key} {value!r} is not a number; the x axis holds numbers")
        return value
    try:
        if isinstance(value, numbers.Real):
            raise TypeError("a number is no date")
        return pd.Timestamp(value)
    except (ValueError, TypeError) as error:
        raise ValueError(f"hairline: timeseries: {key} {value!r} is not a date; the x axis holds dates, such as "
                         "'2024-03-10'") from error


def check_marks(bands: Sequence[Mapping], events: Sequence[Mapping]) -> None:
    """Bands need start and end, events need x."""
    for kind, items, keys in (("band", bands, ("start", "end")), ("event", events, ("x",))):
        for index, item in enumerate(items):
            missing = [key for key in keys if key not in item]
            if missing:
                raise ValueError(f"hairline: timeseries: {kind} {index + 1} needs {' and '.join(keys)}; missing "
                                 f"{', '.join(missing)}")


def draw_marks(ax, bands: Sequence[Mapping], events: Sequence[Mapping], name: str, is_date: bool) -> None:
    settings = current_settings()
    for band in bands:
        if band.get("panels") is None or name in band["panels"]:
            ax.axvspan(as_x(band["start"], is_date, "band start"), as_x(band["end"], is_date, "band end"),
                       color=settings.neutral["band"],
                       zorder=0, linewidth=0)
    for event in events:
        if event.get("panels") is None or name in event["panels"]:
            ax.axvline(as_x(event["x"], is_date, "event x"), **{**reference_style(), "color": settings.neutral["muted"],
                                                     "linestyle": (0, (1, 2))})
            if event.get("label"):
                caption_note(ax, event["label"], as_x(event["x"], is_date, "event x"), settings)


def partial_span(key: object, is_date: bool) -> tuple[object, object]:
    """An incomplete period on the x axis: a year ("2021") or a date on a date axis, a number otherwise; it reaches
    to the next year, day or number."""
    if not is_date:
        start = as_x(float(key) if isinstance(key, str) else key, False, "partial")
        return start - 0.5, start + 0.5
    text = str(key)
    if text.isdigit() and len(text) == 4:
        return pd.Timestamp(f"{text}-01-01"), pd.Timestamp(f"{int(text) + 1}-01-01")
    start = as_x(key, True, "partial")
    return start, start + np.timedelta64(1, "D")


def draw_partial(ax, partial: Mapping[str, str], is_date: bool) -> None:
    """Incomplete periods drawn lighter: a veil of the surface colour over the data there, as bars of an
    incomplete year are drawn lighter."""
    settings = current_settings()
    for key in partial:
        start, end = partial_span(key, is_date)
        ax.axvspan(start, end, color=settings.neutral["surface"], alpha=1 - load_tokens()["partial"]["opacity"],
                   zorder=2.5, linewidth=0, label="_nolegend_")


def legend_items(raw: bool, period_mean: bool, bands: Sequence[Mapping], labels: Mapping[str, str | None],
                 marks: tuple[str, str | None] | None = None) -> list:
    neutral = current_settings().neutral
    items = [("thin", neutral["ink"], labels["raw"])] if raw else []
    items += summary_legend_items(marks) if marks else [("line", neutral["ink"], labels["mean"])]
    if period_mean:
        items.append(("dash", neutral["muted"], "Period mean"))
    if labels["threshold"]:
        items.append(("dash", load_tokens()["reference"]["color"], labels["threshold"]))
    items += [("band", neutral["band"], band["label"]) for band in bands[:1] if band.get("label")]
    return items


def timeseries(data: pd.DataFrame, x: str, y: str, by: str | None = None, *, title: str | None = None,
               subtitle: str | None = None, caption: str | None = None, window: int = 7, raw: bool = True,
               period_mean: bool = False, percent: bool = False, threshold: float | None = None,
               threshold_label: str | None = None, threshold_legend: str | None = None,
               stats: Sequence[str] = ("mean", "median"), share_label: str | None = None, key: str | None = None,
               key_panels: Sequence[str] | None = None, highlight: Sequence[str] | None = None,
               qualifiers: Mapping[str, str] | None = None, bands: Sequence[Mapping] = (),
               events: Sequence[Mapping] = (), order: Sequence[str] | None = None, raw_label: str = "Raw values",
               mean_label: str | None = None, colors: Mapping[str, str] | None = None,
               size: str = "double", partial: Mapping[str, str] | None = None, color_by: str | None = None,
               dimension: str | None = None, clip: float | tuple[float | None, float | None] | None = None,
               clip_stats: bool = False, x_title: str | None = None, y_title: str | None = None,
               reference: Reference = None, key_title: str | None = None,
               summary: str | Sequence[str] | None = None) -> HairlineFigure:
    """One panel per group: raw values thin under a trailing rolling mean, with key numbers in the panel headers.
    `partial` names incomplete periods ({"2021": "2 months"}: a year, a date, or an x value) and what they hold:
    they are drawn lighter and the caption says so. `color_by` colours the panels by a coarser column;
    `dimension` keeps their colours off another dimension's slots. Shared with the other charts: `clip` and
    `clip_stats` (as in `spread()`), `x_title`, `y_title`, `reference` (lines at y values, beside `threshold`) and
    `key_title`.

    `stats` names the key numbers in the panel headers: any of "mean", "median", "iqr", "range", "sd", "ci", "n"
    and "share_above" (with `threshold`). `summary` summarises the values at each x instead of drawing them under
    a rolling mean: the centre as the line, its interval as a band in the series' colour (("median", "iqr"),
    ("mean", "ci"), ("mean", "sd"); "range" with either), both named in the legend."""
    from hairline.charts.common import series_colors
    check_columns(data, [x, y, by, color_by])
    check_window(window)
    check_present(data, y, "timeseries")
    check_numeric(data, [y], "timeseries")
    check_marks(bands, events)
    marks = checked_summary(summary)
    data = with_iso_dates(data, x)
    title = title or (f"{humanise(y)} by {str(by).replace('_', ' ')}" if by else f"{humanise(y)} over time")
    groups = groups_of(data, by, order, "timeseries")
    every = pd.concat([rows[y] for _, rows in groups]).dropna().to_numpy(dtype=float)
    limits = clip_limits(every, clip, "timeseries")
    clipped = clip_caption(every, limits, clip_stats, current_settings().locale) if clip is not None else None
    caption = with_caption(caption, partial_caption(partial, current_settings().locale), clipped)
    result = figure(title, subtitle=subtitle, caption=caption, size=size, panels=len(groups), layout="rows")
    is_date = pd.api.types.is_datetime64_any_dtype(data[x])
    share_label = share_label or f"≥ {formatter(percent)(threshold, 0) if threshold is not None else ''}"
    labels = {"share_above": share_label, **{name: stat_label(name) for name in STAT_NAMES}}
    palette = series_colors([name for name, _ in groups], data, by, color_by, colors, dimension,
                            "timeseries")[0] if by else {}
    for index, (name, rows) in enumerate(groups):
        ax = result.axes[index]
        drawn = rows.assign(**{y: rows[y].where(rows[y].between(*limits))})
        if marks:
            draw_summary_series(ax, drawn, x, y, palette.get(name, lone_color()), marks)
        else:
            draw_series(ax, drawn, x, y, palette.get(name, lone_color()), window, raw)
        if period_mean:
            ax.axhline(rows[y].mean(), **{**reference_style(), "color": current_settings().neutral["muted"],
                                          "linestyle": (0, (3, 2.5))})
        draw_marks(ax, bands, events, name, is_date)
        draw_partial(ax, partial or {}, is_date)
        if percent:
            result.percent_axis(index)
        emphasise = key is not None and (key_panels is None or name in key_panels)
        result.panel_header(index, name or title, (qualifiers or {}).get(name),
                            panel_stats((drawn if clip_stats else rows)[y], stats, percent, threshold, share_label),
                            key=labels.get(key, key) if emphasise else None)
    if threshold is not None:
        result.reference(y=threshold, label=threshold_label)
    if highlight:
        result.highlight(panels=list(highlight))
    labels = {"raw": raw_label, "threshold": threshold_legend, "mean": mean_label or f"Rolling mean ({window})"}
    result.legend(legend_items(raw and not marks, period_mean, list(bands), labels, marks))
    return apply_options(result, "timeseries", x_title=x_title, y_title=y_title, reference=reference,
                         key_title=key_title)
