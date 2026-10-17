"""Small-multiple time series with two levels of detail."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

from hairline import entities
from hairline.charts.common import check_columns
from hairline.figure import HairlineFigure, figure
from hairline.focus import REFERENCE_ID
from hairline.marks import SECONDARY_ID
from hairline.numbers import format_number, format_percent
from hairline.settings import current_settings, role_size
from hairline.tokens import load_tokens

STAT_LABELS = {"mean": "Mean", "median": "Median", "range": "Range"}


def groups_of(data: pd.DataFrame, by: str | None, order: Sequence[str] | None) -> list[tuple[str, pd.DataFrame]]:
    if by is None:
        return [("", data)]
    names = list(order) if order is not None else list(dict.fromkeys(data[by]))
    return [(str(name), data[data[by] == name]) for name in names]


def formatter(percent: bool):
    return (lambda value, digits=1: format_percent(value, digits)) if percent else (
        lambda value, digits=1: format_number(value, digits))


def panel_stats(values: pd.Series, stats: Sequence[str], percent: bool, threshold: float | None,
                share_label: str) -> list[tuple[str, str]]:
    show = formatter(percent)
    pairs = []
    for stat in stats:
        if stat == "share_above":
            if threshold is None:
                raise ValueError("hairline: stats 'share_above' needs threshold=")
            pairs.append((share_label, format_percent(float((values >= threshold).mean()), 0)))
        elif stat == "range":
            pairs.append(("Range", f"{show(values.min(), 0)}–{show(values.max(), 0)}"))
        elif stat in STAT_LABELS:
            pairs.append((STAT_LABELS[stat], show(getattr(values, stat)())))
        else:
            raise ValueError(f"hairline: unknown stat {stat!r}; use mean, median, range or share_above")
    return pairs


def draw_series(ax, rows: pd.DataFrame, x: str, y: str, color: str, window: int, raw: bool) -> None:
    lines, base = load_tokens()["lines"], current_settings().base_size
    rows = rows.sort_values(x)
    if raw:
        ax.plot(rows[x], rows[y], color=color, linewidth=lines["secondary"] * base, alpha=lines["secondary_opacity"],
                gid=SECONDARY_ID)
    smooth = rows[y].rolling(window, min_periods=1).mean()
    ax.plot(rows[x], smooth, color=color, linewidth=lines["data"] * base)


def reference_style() -> dict:
    rules, base = load_tokens()["reference"], current_settings().base_size
    return {"color": rules["color"], "linewidth": rules["width"] * base, "gid": REFERENCE_ID, "label": "_nolegend_"}


def caption_note(ax, text: str, x: object, settings) -> None:
    """Event label at the bottom of the panel, right of its line (the top holds thresholds and their labels)."""
    gap = load_tokens()["reference"]["label_gap"] * role_size(settings, "caption")
    ax.annotate(text, xy=(x, 0), xycoords=("data", "axes fraction"), xytext=(gap, gap), textcoords="offset points",
                ha="left", va="bottom", fontsize=role_size(settings, "caption"), color=settings.neutral["faint"],
                fontfamily=settings.font, annotation_clip=False)


def as_x(value: object, is_date: bool) -> object:
    return pd.Timestamp(value) if is_date else value


def draw_marks(ax, bands: Sequence[Mapping], events: Sequence[Mapping], name: str, is_date: bool) -> None:
    settings = current_settings()
    for band in bands:
        if band.get("panels") is None or name in band["panels"]:
            ax.axvspan(as_x(band["start"], is_date), as_x(band["end"], is_date), color=settings.neutral["band"],
                       zorder=0, linewidth=0)
    for event in events:
        if event.get("panels") is None or name in event["panels"]:
            ax.axvline(as_x(event["x"], is_date), **{**reference_style(), "color": settings.neutral["muted"],
                                                     "linestyle": (0, (1, 2))})
            if event.get("label"):
                caption_note(ax, event["label"], as_x(event["x"], is_date), settings)


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


def timeseries(data: pd.DataFrame, x: str, y: str, by: str | None = None, *, title: str,
               subtitle: str | None = None, caption: str | None = None, window: int = 7, raw: bool = True,
               period_mean: bool = False, percent: bool = False, threshold: float | None = None,
               threshold_label: str | None = None, threshold_legend: str | None = None,
               stats: Sequence[str] = ("mean", "median"), share_label: str | None = None, key: str | None = None,
               key_panels: Sequence[str] | None = None, highlight: Sequence[str] | None = None,
               qualifiers: Mapping[str, str] | None = None, bands: Sequence[Mapping] = (),
               events: Sequence[Mapping] = (), order: Sequence[str] | None = None, raw_label: str = "Raw values",
               mean_label: str | None = None, size: str = "double") -> HairlineFigure:
    """One panel per group: raw values thin under a trailing rolling mean, with key numbers in the panel headers."""
    check_columns(data, [x, y, by])
    groups = groups_of(data, by, order)
    result = figure(title, subtitle=subtitle, caption=caption, size=size, panels=len(groups), layout="rows")
    is_date = pd.api.types.is_datetime64_any_dtype(data[x])
    share_label = share_label or f"≥ {formatter(percent)(threshold, 0) if threshold is not None else ''}"
    labels = {"share_above": share_label, **STAT_LABELS}
    for index, (name, rows) in enumerate(groups):
        ax = result.axes[index]
        draw_series(ax, rows, x, y, entities.color(name) if by else current_settings().palette[0], window, raw)
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
