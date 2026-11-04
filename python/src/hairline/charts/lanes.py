"""Lanes over the time of day: one row per place, the time of day across, each cell coloured by the share of days
the place was occupied then, in its group's ramp, binned as the legend row's key; moves between places as faint
connectors in the gaps between rows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection, PolyCollection

from hairline import entities
from hairline.charts.common import check_columns, check_labels, humanise, ordered_names
from hairline.charts.time_of_day import (
    MINUTES,
    add_caption,
    add_legend,
    binned,
    calendar,
    check_bin,
    check_steps,
    clock,
    clock_hours,
    day_count,
    day_origin,
    hour_span,
    interval_rows,
    kept_rows,
    minute_counts,
    row_layout,
    separators,
    step_colors,
    step_index,
    target_panels,
)
from hairline.figure import HairlineFigure, figure
from hairline.marks import lone_color
from hairline.numbers import format_number, format_percent, word
from hairline.settings import current_settings
from hairline.tokens import load_tokens

VALUES = ("share", "count")
FLOW_COLUMNS = ("from", "to", "time")


def lane_rows(data: pd.DataFrame, row: str, group: str | None, order: Sequence[str] | None) -> tuple[list[str],
                                                                                                    list[str] | None]:
    """Rows top to bottom: by group (in data order), then in `order` or data order within it."""
    check_labels(data, [row] + ([group] if group else []), "lanes")
    names = ordered_names(data[row], order, "lanes", row)
    if group is None:
        return names, None
    owners = data.assign(_row=data[row].astype(str)).groupby("_row", sort=False)[group].agg(
        lambda values: list(dict.fromkeys(values.astype(str))))
    split = [name for name in names if len(owners[name]) > 1]
    if split:
        raise ValueError(f"hairline: lanes: row '{split[0]}' belongs to more than one {group}: "
                         f"{', '.join(owners[split[0]])}")
    blocks = list(dict.fromkeys(owners[name][0] for name in names))
    rows = [name for block in blocks for name in names if owners[name][0] == block]
    return rows, [owners[name][0] for name in rows]


def interval_matrix(data: pd.DataFrame, rows: list[str], row: str, start: str, end: str, bin_minutes: int,
                    days: object, value: str) -> tuple[dict[str, np.ndarray], str, tuple[pd.Timestamp, list[int]]]:
    """Per row the value per bin of the day over the days kept: the share of days occupied, or the mean number of
    intervals at the same time."""
    starts, ends = interval_rows(data, start, end, "lanes")
    origin, total = day_origin(starts), day_count(starts, ends)
    kept, label = calendar(origin, origin + np.timedelta64(total - 1, "D"), days, "lanes")
    chosen = kept_rows(kept, origin)
    names, found = data[row].astype(str), {}
    for name in rows:
        mask = (names == name).to_numpy()
        minutes = minute_counts(starts[mask], ends[mask], origin, total)
        cells = binned(minutes, bin_minutes, "any" if value == "share" else "peak")[chosen]
        found[name] = cells.mean(axis=0).astype(float)
    return found, label, (origin, list(chosen))


def share_matrix(data: pd.DataFrame, rows: list[str], row: str, start: str, amount: str,
                 bin_minutes: int) -> dict[str, np.ndarray]:
    """A precomputed share per row and bin start (07:15 or 7.25): each value in its bin of the day."""
    hours = clock_hours(data[start], start, "lanes")
    bins = np.floor(hours * 60 / bin_minutes + 1e-9).astype(int) % (MINUTES // bin_minutes)
    names, found = data[row].astype(str).to_numpy(), {}
    values = data[amount].to_numpy(dtype=float)
    for name in rows:
        cells = np.zeros(MINUTES // bin_minutes)
        mask = names == name
        np.maximum.at(cells, bins[mask], np.nan_to_num(values[mask]))
        found[name] = cells
    return found


def flow_segments(flows: pd.DataFrame, columns: Sequence[str], rows: list[str], ys: dict[str, float],
                  colours: dict[str, str], bin_minutes: int, days: int, options: dict) -> tuple[list, list]:
    """One connector per (from, to, bin) between the two rows, its opacity the moves per day against the
    reference (the busiest connector by default), rare ones below the floor left out."""
    source, target, time = columns
    check_columns(flows, [source, target, time])
    unknown = sorted({str(name) for name in pd.concat([flows[source], flows[target]]).astype(str)} - set(rows))
    if unknown:
        raise ValueError(f"hairline: lanes: flows name '{unknown[0]}', which is not a row; rows: {', '.join(rows)}")
    bins = np.floor(clock_hours(flows[time], time, "lanes") * 60 / bin_minutes + 1e-9).astype(int)
    moves = pd.DataFrame({"from": flows[source].astype(str), "to": flows[target].astype(str), "bin": bins})
    counts = moves.value_counts()
    per_day = counts / days
    reference = options["flow_reference"] or float(per_day.max())
    floor = options["flow_floor"] if options["flow_floor"] is not None else \
        load_tokens()["lanes"]["flow_floor"] * reference
    segments, styles = [], []
    for (start, end, bin_index), rate in per_day.items():
        if rate < floor or start == end:
            continue
        x = (bin_index + 0.5) * bin_minutes / 60
        segments.append([(x, ys[start]), (x, ys[end])])
        styles.append((colours[end], min(1.0, rate / reference)))
    return segments, styles


def draw_cells(result: HairlineFigure, index: int, matrix: dict[str, np.ndarray], ys: dict[str, float],
               colours: dict[str, str], ramps: dict[str, list[str]], steps: list[float], options: dict) -> None:
    """Rectangles per occupied bin, coloured by the bin of their value; each a tooltip target."""
    half, bin_minutes = load_tokens()["lanes"]["cell"] / 2, options["bin"]
    polygons, faces = [], []
    for name, values in matrix.items():
        for bin_index, amount in enumerate(values):
            if amount <= 0:
                continue
            low, high = hour_span(bin_index, bin_minutes)
            y = ys[name]
            share = amount / options["top"]
            polygons.append([(low, y - half), (high, y - half), (high, y + half), (low, y + half)])
            faces.append(ramps[colours[name]][step_index(share, steps)])
            shown = format_percent(amount, 0) if options["value"] == "share" else format_number(amount, 1)
            result.hover(index, name, colours[name], (low, y - half, high, y + half),
                         f"{name}, {clock(low)}–{clock(high)}: {shown}")
    result.axes[index].add_collection(PolyCollection(polygons, facecolors=faces, edgecolors="none", linewidths=0,
                                                     zorder=2), autolim=True)


def lanes(data: pd.DataFrame, row: str, start: str, end: str | None = None, *, group: str | None = None,
          bin: int | None = None, value: str = "share", days: object = None, amount: str | None = None,
          order: Sequence[str] | None = None, flows: pd.DataFrame | None = None,
          flow_columns: Sequence[str] = FLOW_COLUMNS, flow_reference: float | None = None,
          flow_floor: float | None = None, steps: Sequence[float] | None = None,
          hours: tuple[float, float] | None = None, spans: Mapping[str, tuple[float, float]] | None = None,
          colors: Mapping[str, str] | None = None, dimension: str | None = None, key_title: str | None = None,
          title: str | None = None, subtitle: str | None = None, caption: str | None = None, size: str = "double",
          into: HairlineFigure | None = None, panel: int = 0) -> HairlineFigure:
    """One row per place over the time of day, from intervals (`start` and `end`, dates with times) per `row`.
    Each `bin`-minute cell shows the share of days the place was occupied then (`value="share"`), or the mean
    number of intervals at once (`value="count"`), in the colour of the row's `group`, binned at `steps` as the
    key in the legend row shows. `group` draws the rows as blocks: its name once in its colour, the rows by number.
    `days` filters the calendar ("weekdays", "weekends", a list of dates), named with its n in the subtitle.
    Without `end`, `start` holds each cell's time of day and `amount` its precomputed share.

    `flows` (a frame of from, to and time; `flow_columns` names them) adds the moves between rows: one faint
    connector per pair and bin, stronger the more moves per day (against `flow_reference`, the busiest by
    default; those below `flow_floor` per day are left out), in the colour of the row moved to.

    The x axis is the time of day, cropped to the hours with data (or `hours`); `spans` shades named periods.
    `into` and `panel` draw into a panel of a figure from `hl.figure()`, so lanes, counts and days share one
    time axis."""
    if value not in VALUES:
        raise ValueError(f"hairline: lanes: value {value!r} must be one of {', '.join(VALUES)}")
    check_columns(data, [row, start, end, group, amount])
    if end is None and amount is None:
        raise ValueError("hairline: lanes: give end= (intervals) or amount= (a precomputed share per cell)")
    bin_minutes, steps = check_bin(bin or load_tokens()["lanes"]["bin"], "lanes"), check_steps(steps, "lanes")
    rows, groups = lane_rows(data, row, group, order)
    if end is not None:
        matrix, day_label, (_, chosen) = interval_matrix(data, rows, row, start, end, bin_minutes, days, value)
    else:
        matrix, day_label, chosen = share_matrix(data, rows, row, start, amount, bin_minutes), None, []
    top = 1.0 if value == "share" else max(float(values.max()) for values in matrix.values()) or 1.0
    names = list(dict.fromkeys(groups)) if groups else []
    with entities.chart(names, colors, dimension) as palette:
        lone = lone_color()
        blocks, ys, colours = row_layout(rows, groups, dict(palette), lone)
    ramps = {colour: step_colors(colour, len(steps)) for colour in set(colours.values())}
    locale = current_settings().locale
    subtitle_text = " · ".join(part for part in (subtitle, day_label) if part) or None

    def make() -> HairlineFigure:
        made = figure(title or f"{humanise(row)} over the day", subtitle=subtitle_text, caption=caption, size=size,
                      height_mm=40)
        made.min_plot = len(rows) * load_tokens()["lanes"]["row_pitch"]
        return made
    result, (index,) = target_panels(into, panel, 1, make)
    ax = result.axes[index]
    draw_cells(result, index, matrix, ys, colours, ramps, steps, {"bin": bin_minutes, "value": value, "top": top})
    if flows is not None:
        segments, styles = flow_segments(flows, flow_columns, rows, ys, colours, bin_minutes, max(len(chosen), 1),
                                         {"flow_reference": flow_reference, "flow_floor": flow_floor})
        width = load_tokens()["lanes"]["flow_width"] * result.settings.base_size
        ax.add_collection(LineCollection(segments, colors=[color for color, _ in styles], linewidths=width,
                                         alpha=None, zorder=1), autolim=True)
        ax.collections[-1].set_alpha([alpha for _, alpha in styles])
    if groups:
        separators(ax, blocks, load_tokens()["reference"]["width"] * result.settings.base_size,
                   result.settings.neutral["axis"])
        result.row_blocks(index, blocks)
    else:
        result.categories(index, list(reversed(rows)), "y")
    ax.set_ylim(-0.5, len(rows) - 0.5)
    occupied = [bin_index for values in matrix.values() for bin_index in np.flatnonzero(values > 0)]
    if not occupied:
        raise ValueError("hairline: lanes: no row is occupied in any bin of the days kept")
    ax.update_datalim([(hour_span(min(occupied), bin_minutes)[0], 0), (hour_span(max(occupied), bin_minutes)[1], 0)])
    result.time_axis(index, hours, spans)
    key_colors = ramps[next(iter(ramps))] if len(ramps) == 1 else step_colors(None, len(steps))
    result.legend_ramp(key_colors, [step * top for step in steps], key_title or word("share_of_days", locale),
                       "percent" if value == "share" else "number", limits=(0.0, top))
    add_legend(result, [("line", result.settings.neutral["muted"], word("move", locale))] if flows is not None else [])
    if into is not None and day_label:
        add_caption(result, f"{day_label}.")
    return result
