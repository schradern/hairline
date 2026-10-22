"""Small-multiple time series with two levels of detail."""

from __future__ import annotations

import math
import numbers
from collections.abc import Mapping, Sequence

import pandas as pd

from hairline import entities
from hairline.charts.common import check_columns, check_labels, check_numeric, check_present, humanise, ordered_names
from hairline.figure import HairlineFigure, figure
from hairline.focus import REFERENCE_ID
from hairline.fonts import families
from hairline.marks import SECONDARY_ID, lone_color
from hairline.numbers import auto_digits, format_number, format_percent, is_whole, quantile_places
from hairline.settings import current_settings, role_size
from hairline.tokens import load_tokens

STAT_LABELS = {"mean": "Mean", "median": "Median", "range": "Range"}


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


def panel_stats(values: pd.Series, stats: Sequence[str], percent: bool, threshold: float | None,
                share_label: str) -> list[tuple[str, str]]:
    show, clean = formatter(percent), values.dropna().astype(float)
    digits = auto_digits(clean * (100 if percent else 1))
    extra = 1 if is_whole(clean) and not percent else 0
    pairs = []
    for stat in stats:
        if stat == "share_above":
            if threshold is None:
                raise ValueError("hairline: stats 'share_above' needs threshold=")
            pairs.append((share_label, format_percent(float((clean >= threshold).mean()), 0)))
        elif stat == "range":
            pairs.append(("Range", f"{show(clean.min(), digits)}–{show(clean.max(), digits)}"))
        elif stat in STAT_LABELS:
            value = getattr(clean, stat)()
            places = digits + extra if stat == "mean" else quantile_places(value, digits, bool(extra))
            pairs.append((STAT_LABELS[stat], show(value, places)))
        else:
            raise ValueError(f"hairline: unknown stat {stat!r}; use mean, median, range or share_above")
    return pairs


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


def legend_items(raw: bool, period_mean: bool, bands: Sequence[Mapping], labels: Mapping[str, str | None]) -> list:
    neutral = current_settings().neutral
    items = [("thin", neutral["ink"], labels["raw"])] if raw else []
    items.append(("line", neutral["ink"], labels["mean"]))
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
               size: str = "double") -> HairlineFigure:
    """One panel per group: raw values thin under a trailing rolling mean, with key numbers in the panel headers."""
    check_columns(data, [x, y, by])
    check_window(window)
    check_present(data, y, "timeseries")
    check_numeric(data, [y], "timeseries")
    check_marks(bands, events)
    data = with_iso_dates(data, x)
    title = title or (f"{humanise(y)} by {str(by).replace('_', ' ')}" if by else f"{humanise(y)} over time")
    groups = groups_of(data, by, order, "timeseries")
    result = figure(title, subtitle=subtitle, caption=caption, size=size, panels=len(groups), layout="rows")
    is_date = pd.api.types.is_datetime64_any_dtype(data[x])
    share_label = share_label or f"≥ {formatter(percent)(threshold, 0) if threshold is not None else ''}"
    labels = {"share_above": share_label, **STAT_LABELS}
    palette = entities.colors_for([name for name, _ in groups], colors) if by else {}
    for index, (name, rows) in enumerate(groups):
        ax = result.axes[index]
        draw_series(ax, rows, x, y, palette.get(name, lone_color()), window, raw)
        if period_mean:
            ax.axhline(rows[y].mean(), **{**reference_style(), "color": current_settings().neutral["muted"],
                                          "linestyle": (0, (3, 2.5))})
        draw_marks(ax, bands, events, name, is_date)
        if percent:
            result.percent_axis(index)
        emphasise = key is not None and (key_panels is None or name in key_panels)
        result.panel_header(index, name or title, (qualifiers or {}).get(name),
                            panel_stats(rows[y], stats, percent, threshold, share_label),
                            key=labels.get(key, key) if emphasise else None)
    if threshold is not None:
        result.reference(y=threshold, label=threshold_label)
    if highlight:
        result.highlight(panels=list(highlight))
    result.legend(legend_items(raw, period_mean, list(bands), {"raw": raw_label, "threshold": threshold_legend,
                                                                "mean": mean_label or f"Rolling mean ({window})"}))
    return result
