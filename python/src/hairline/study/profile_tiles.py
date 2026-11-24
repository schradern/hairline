"""The tiles of profile(): a histogram per number, bars of shares per category, counts per period per date column,
each stacked by group when the profile has groups."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from hairline import entities
from hairline.charts.bars import value_label
from hairline.figure import HairlineFigure, figure
from hairline.marks import FIXED_ID, context_color, lone_color
from hairline.numbers import format_number, is_whole
from hairline.stats.density import quantiles
from hairline.stats.histogram import bin_edges, counts_in
from hairline.study.columns import is_missing, level_text, levels, numbers
from hairline.study.profile_strata import MISSING, Stratum, fill, stack
from hairline.study.summaries import count_share, counted_text, digits_for, summary_numbers, summary_text
from hairline.tokens import load_tokens

if TYPE_CHECKING:
    from hairline.study.model import Study

PERIODS = {"M": "month", "Q": "quarter", "Y": "year"}


def missing_note(column: pd.Series, *before: str) -> str | None:
    """The header's qualifier: what the tile counts in (`before`), then '9 missing' when values are; it sits beside
    the name, where it is never dropped for room."""
    missing = int(is_missing(column).sum())
    parts = [*before, f"{format_number(missing, 0)} missing" if missing else ""]
    return ", ".join(part for part in parts if part) or None


def in_group(stratum: Stratum) -> str:
    return f", {stratum.name}" if stratum.name else ""


def bin_text(left: float, width: float, whole: bool, digits: int) -> str:
    """A bin as a reader names it: '4' for a bin one whole number wide, else '60 to under 65'."""
    if whole and width == 1:
        return format_number(left + 0.5, 0)
    places = 0 if whole else digits
    return f"{format_number(left, places)} to under {format_number(left + width, places)}"


def count_limits(result: HairlineFigure, index: int, totals) -> None:
    """Counts from zero to a little above the tallest bar, so its top never touches the panel's edge."""
    result.axes[index].set_ylim(0, max(max(totals), 1) * (1 + load_tokens()["profile"]["count_headroom"]))


def numeric_tile(result: HairlineFigure, index: int, study: Study, name: str, groups: tuple) -> None:
    """A histogram on round bins shared by every group, the median of all as an ink line; the header gives median
    (IQR) and what is missing."""
    column, label = study.data[name], study.label(name)
    values, (strata, colors) = numbers(column), groups
    found = summary_numbers(values, ("median_iqr",), int(is_missing(column).sum()))
    stats = [("Median (IQR)", summary_text(found, "median_iqr", digits_for(values), is_whole(values)))]
    result.panel_header(index, label, missing_note(column), stats=stats, x_title=study.measure(name))
    result.integer_axis(index, "y")
    if not len(values):
        return
    whole, edges = is_whole(values), bin_edges(values, is_whole(values))
    width = float(edges[1] - edges[0])
    parts = [(stratum, counts_in(numbers(column[stratum.mask]), edges)) for stratum in strata]
    sizes = {stratum.name: len(numbers(column[stratum.mask])) for stratum in strata}

    def tip(spot: int, stratum: Stratum, count: float) -> str:
        span = " ".join(filter(None, [bin_text(edges[spot], width, whole, digits_for(values)), study.measure(name)]))
        return f"{label} {span}{in_group(stratum)}: {count_share(int(count), sizes[stratum.name])}"
    lefts = [float(edge) for edge in edges[:-1]]
    totals = stack(result, index, colors, parts, {"spots": lefts, "sizes": width, "horizontal": False,
                                                  "extents": [(left, left + width) for left in lefts],
                                                  "series": label}, tip)
    count_limits(result, index, totals)
    median = quantiles(values, [0.5])[0]
    result.axes[index].plot([median, median], [0, max(totals)], color=result.settings.neutral["ink"], gid=FIXED_ID,
                            linewidth=load_tokens()["reference"]["width"] * result.settings.base_size,
                            solid_capstyle="butt")


def categorical_tile(result: HairlineFigure, index: int, study: Study, name: str, groups: tuple) -> None:
    """One bar per level, its share of the non-missing values written at its end, split by group; short lists keep
    thin bars."""
    rules = load_tokens()["profile"]
    column, label, (strata, colors) = study.data[name], study.label(name), groups
    present = column.map(level_text).where(~is_missing(column))
    names = levels(column)
    result.panel_header(index, label, missing_note(column))
    result.percent_axis(index, "x")
    if not names:
        return
    total = int(present.notna().sum())
    parts = [(stratum, [int((present[stratum.mask] == level).sum()) / total for level in names])
             for stratum in strata]
    spots, half = [len(names) - 1 - position for position in range(len(names))], rules["bar_height"] / 2

    def tip(spot: int, stratum: Stratum, share: float) -> str:
        return f"{label} {names[spot]}{in_group(stratum)}: {count_share(round(share * total), total)}"
    shares = stack(result, index, colors, parts, {"spots": spots, "sizes": rules["bar_height"], "horizontal": True,
                                                  "extents": [(y - half, y + half) for y in spots], "series": label},
                   tip)
    ax, slots = result.axes[index], max(len(names), rules["min_slots"])
    for y, share in zip(spots, shares, strict=True):
        value_label(ax, share, (share, y), True, True)
    result.categories(index, list(reversed(names)), "y")
    ax.set_ylim(len(names) - 0.5 - slots, len(names) - 0.5)
    ax.set_xlim(0, 1)


def period_of(first: pd.Timestamp, last: pd.Timestamp) -> str:
    """Months while they stay few enough to read as bars, then quarters, then years."""
    rules = load_tokens()["profile"]
    months = (last.year - first.year) * 12 + last.month - first.month + 1
    return "M" if months <= rules["month_bars"] else "Q" if months / 3 <= rules["quarter_bars"] else "Y"


def without_zone(dates: pd.Series) -> pd.Series:
    return dates.dt.tz_localize(None) if dates.dt.tz is not None else dates


def month_text(day: pd.Timestamp, result: HairlineFigure) -> str:
    """'Jan 2023' in the figure's locale: short enough for a tile's header; the table keeps the exact dates."""
    return f"{load_tokens()['locales'][result.settings.locale]['months'][day.month - 1]} {day.year}"


def date_tile(result: HairlineFigure, index: int, study: Study, name: str, dates: pd.Series, groups: tuple) -> None:
    """Bars of rows per month (quarter, year) over the whole period, split by group; the header names the first
    and last month."""
    label, column, (strata, colors) = study.label(name), study.data[name], groups
    if not len(dates):
        result.panel_header(index, label, missing_note(column))
        return
    dates = without_zone(dates)
    period = period_of(dates.min(), dates.max())
    every = pd.period_range(dates.min(), dates.max(), freq=period)
    periods = dates.dt.to_period(period)
    in_rows = pd.Series(np.arange(len(study.data)), index=study.data.index).loc[dates.index].to_numpy()
    parts = [(stratum, periods[stratum.mask[in_rows]].value_counts().reindex(every, fill_value=0).to_numpy())
             for stratum in strata]
    stats = [("From", f"{month_text(dates.min(), result)} to {month_text(dates.max(), result)}")]
    result.panel_header(index, label, missing_note(column, f"per {PERIODS[period]}"), stats=stats)
    result.integer_axis(index, "y")
    starts = [item.start_time.to_pydatetime() for item in every]
    widths = [(item + 1).start_time.to_pydatetime() - start for item, start in zip(every, starts, strict=True)]
    extents = [(mdates.date2num(start), mdates.date2num(start + width)) for start, width in zip(starts, widths,
                                                                                                strict=True)]

    def tip(spot: int, stratum: Stratum, count: float) -> str:
        return f"{label} {every[spot]}{in_group(stratum)}: {format_number(count, 0)}"
    totals = stack(result, index, colors, parts, {"spots": starts, "sizes": widths, "horizontal": False,
                                                  "extents": extents, "series": label}, tip)
    count_limits(result, index, totals)


def profile_columns(size: str, tiles: int) -> int:
    """Three tiles a row across a page, two in a column and a half, one in a single column."""
    widths = {"single": 1, "onehalf": 2}
    return min(tiles, widths.get(size, load_tokens()["profile"]["columns"]))


def group_colors(result: HairlineFigure, strata: list[Stratum], by_label: str | None) -> dict[str | None, str]:
    """One colour for the whole cohort; else the session's colour of each group, grey for rows without one, and
    the legend row naming them."""
    surface = result.settings.neutral["surface"]
    if strata[0].name is None:
        return {None: fill(lone_color(result.settings), surface)}
    named = [stratum.name for stratum in strata if stratum.name != MISSING]
    colors = {name: fill(color, surface) for name, color in {**entities.colors_for(named),
                                                              MISSING: context_color(result.settings)}.items()}
    result.legend([("square", colors[stratum.name], stratum.name) for stratum in strata])
    result.key_title(by_label)
    return colors


def profile_figure(study: Study, dates: dict[str, pd.Series], strata: list[Stratum], by: str | None,
                   size: str) -> HairlineFigure | None:
    """One tile per variable, in the order given, the date columns last."""
    names = [*study.variables, *dates]
    if not names:
        return None
    rules = load_tokens()["profile"]
    columns = profile_columns(size, len(names))
    rows = math.ceil(len(names) / columns)
    result = figure("Characteristics of the cohort", subtitle=counted_text(len(study.data), study.nouns),
                    size=size, height_mm=rules["frame_mm"] + rows * rules["tile_mm"], panels=len(names),
                    layout="compose", columns=columns)
    groups = (strata, group_colors(result, strata, study.label(by) if by else None))
    for index, name in enumerate(names):
        if name in dates:
            date_tile(result, index, study, name, dates[name], groups)
        elif study.types[name] == "numeric":
            numeric_tile(result, index, study, name, groups)
        else:
            categorical_tile(result, index, study, name, groups)
    return result
