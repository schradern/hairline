"""Tick positions, tick labels and their visibility for hairline panels."""

from __future__ import annotations

import math

import matplotlib.dates as mdates
from matplotlib.axes import Axes
from matplotlib.axis import Axis
from matplotlib.ticker import FixedLocator, FuncFormatter, ScalarFormatter

from hairline.layout.measure import text_width
from hairline.numbers import format_compact, format_number, format_percent, number_unit
from hairline.ticks import axis_limits, month_breaks, month_label, nice_breaks
from hairline.tokens import load_tokens


def decimals_for(step: float) -> int:
    digits = max(0, -math.floor(math.log10(step) + 1e-9))
    while abs(step * 10 ** digits - round(step * 10 ** digits)) > 1e-9 and digits < 10:
        digits += 1
    return digits


def is_date_axis(axis: Axis) -> bool:
    converter = axis.get_converter() if hasattr(axis, "get_converter") else axis.converter
    return converter is not None and "Date" in type(converter).__name__


def configure_date_ticks(ax: Axes, locale: str) -> list[str]:
    """Month ticks with the year at January, the same rule as the R package."""
    low, high = (mdates.num2date(value).date() for value in sorted(ax.get_xlim()))
    days = month_breaks(low, high)
    ax.xaxis.set_major_locator(FixedLocator([mdates.date2num(day) for day in days]))
    labels = {round(mdates.date2num(day), 6): month_label(day, locale) for day in days}
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _position=None: labels.get(round(value, 6), "")))
    return list(labels.values())


def is_numeric_axis(axis: Axis) -> bool:
    converter = axis.get_converter() if hasattr(axis, "get_converter") else axis.converter
    formatter = axis.get_major_formatter()
    return converter is None and isinstance(formatter, (ScalarFormatter, FuncFormatter))


def data_interval(axes: list[Axes], which: str) -> tuple[float, float]:
    """Union of the data ranges of `axes` along one direction; (0, 1) when there is no data."""
    values = [value for ax in axes for value in (ax.dataLim.intervaly if which == "y" else ax.dataLim.intervalx)
              if math.isfinite(value)]
    return (min(values), max(values)) if values else (0.0, 1.0)


def axis_breaks(ax: Axes, which: str, interval: tuple[float, float] | None, target: int) -> list[float]:
    if interval is not None:
        return nice_breaks(*interval, target=target)
    low, high = sorted(ax.get_ylim() if which == "y" else ax.get_xlim())
    return [value for value in nice_breaks(low, high, target=target) if low - 1e-12 <= value <= high + 1e-12]


def tick_formatter(breaks: list[float], percent: bool, locale: str) -> FuncFormatter:
    """Locale labels with the decimals the step needs; numbers from 10^9 on in one short-scale unit for the whole
    axis (0, 0.5 tn, 1 tn), so that thirteen digits never crowd an axis."""
    step = breaks[1] - breaks[0] if len(breaks) > 1 else 1.0
    unit = None if percent else number_unit(breaks, locale)
    digits = decimals_for(step * (100 if percent else 1) / (unit[0] if unit else 1))
    top = breaks[-1]

    def label(value: float, _position: object = None) -> str:
        if percent:
            return format_percent(value, digits, locale) if math.isclose(value, top) else format_number(
                value * 100, digits, locale)
        return format_compact(value, digits, unit, locale)
    return FuncFormatter(label)


def configure_ticks(ax: Axes, which: str, interval: tuple[float, float] | None, percent: bool, locale: str,
                    target: int = 5) -> list[str]:
    """Set nice breaks and locale labels on a numeric axis; `interval` None keeps the user's limits."""
    axis = ax.yaxis if which == "y" else ax.xaxis
    if which == "x" and is_date_axis(axis):
        if interval is not None:
            ax.set_xlim(*interval, auto=False)
        return configure_date_ticks(ax, locale)
    if not is_numeric_axis(axis):
        return [label.get_text() for label in axis.get_ticklabels()]
    breaks = axis_breaks(ax, which, interval, target)
    if interval is not None:
        (ax.set_ylim if which == "y" else ax.set_xlim)(*axis_limits(*interval, breaks), auto=False)
    axis.set_major_locator(FixedLocator(breaks))
    formatter = tick_formatter(breaks, percent, locale)
    axis.set_major_formatter(formatter)
    return [formatter(value) for value in breaks]


def label_width(labels: list[str], family: str, size: float) -> float:
    return max((text_width(label, family, size) for label in labels), default=0.0)


def edge_alignment(offset: float) -> str:
    """Labels at the plot's left or right edge align inward, so they stay clear of the y labels and the margin."""
    tolerance = load_tokens()["ticks"]["edge_tolerance"]
    return "left" if offset <= tolerance else "right" if offset >= 1 - tolerance else "center"


def align_edge_labels(ax: Axes) -> None:
    low, high = ax.get_xlim()
    locations = ax.xaxis.get_majorticklocs()
    for tick, location in zip(ax.xaxis.get_major_ticks(len(locations)), locations, strict=True):
        tick.label1.set_horizontalalignment(edge_alignment((location - low) / (high - low)))


def set_tick_visibility(ax: Axes, show_x: bool, show_y: bool, y_pad: float, x_pad: float) -> None:
    ax.tick_params(axis="x", labelbottom=show_x, pad=x_pad)
    ax.tick_params(axis="y", labelleft=show_y, pad=y_pad)
