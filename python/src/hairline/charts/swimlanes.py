"""Swimlanes for one day: a bar per interval in its row (which patient is where, which person covers them), the
label inside when it fits, an inner interval as a darker band along its lower edge (the narcosis within the stay),
rows in named blocks and the time-of-day axis; tasks can be given to the first free person."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

from hairline import entities
from hairline.charts.common import check_columns, check_labels, humanise, ordered_names
from hairline.charts.correlation_geometry import text_color
from hairline.charts.time_of_day import add_legend, clock, first_free, row_layout, separators, target_panels
from hairline.charts.timeseries import iso_datetimes
from hairline.color.space import hex_to_oklch, oklch_to_hex
from hairline.figure import HairlineFigure, figure
from hairline.fonts import families
from hairline.marks import STATIC_ID, lone_color
from hairline.settings import current_settings, role_size
from hairline.tokens import load_tokens

ASSIGN = ("first_free", None)
# How much darker the inner interval is drawn, in OKLCH lightness.
INNER_DARKER = 0.22


def day_hours(data: pd.DataFrame, columns: Sequence[str], optional: Sequence[str] = ()) -> dict[str, np.ndarray]:
    """Each column as hours since midnight of the first day: numbers as they are, dates relative to that day (a
    stay past midnight reads 25.5). `optional` columns may be missing in a row (no inner interval there)."""
    found, times = {}, {}
    for column in columns:
        values = data[column]
        if pd.api.types.is_numeric_dtype(values) and not pd.api.types.is_bool_dtype(values):
            found[column] = values.to_numpy(dtype=float)
        else:
            times[column] = values if pd.api.types.is_datetime64_any_dtype(values) else iso_datetimes(values)
            unreadable = times[column].isna() & values.notna() if column in optional else times[column].isna()
            if unreadable.any():
                raise ValueError(f"hairline: swimlanes: '{column}' needs times (07:15 as 7.25, or dates with times)")
    if times:
        origin = min(value.min() for value in times.values() if value.notna().any()).normalize()
        found |= {column: ((value - origin).dt.total_seconds() / 3600).to_numpy(dtype=float)
                  for column, value in times.items()}
    return found


def assigned_rows(data: pd.DataFrame, group: str | None, hours: dict[str, np.ndarray], start: str,
                  end: str) -> pd.Series:
    """Rows named by person: within each group, each task to the first person free at its start (1, 2, …)."""
    labels = (data[group].astype(str) if group else pd.Series([""] * len(data), index=data.index)).to_numpy()
    people = np.empty(len(data), dtype=object)
    for name in dict.fromkeys(labels):
        mask = labels == name
        numbers = first_free(list(hours[start][mask]), list(hours[end][mask]))
        people[mask] = [f"{name} {number}".strip() for number in numbers]
    return pd.Series(people, index=data.index)


def darker(color: str) -> str:
    lightness, chroma, hue = hex_to_oklch(color)
    return oklch_to_hex(max(0.0, lightness - INNER_DARKER), chroma, hue)


def swimlanes(data: pd.DataFrame, row: str | None, start: str, end: str, *, label: str | None = None,
              color_by: str | None = None, inner: tuple[str, str] | None = None, group: str | None = None,
              assign: str | None = None, order: Sequence[str] | None = None,
              hours: tuple[float, float] | None = None, spans: Mapping[str, tuple[float, float]] | None = None,
              colors: Mapping[str, str] | None = None, dimension: str | None = None, title: str | None = None,
              subtitle: str | None = None, caption: str | None = None, size: str = "double",
              into: HairlineFigure | None = None, panel: int = 0) -> HairlineFigure:
    """One bar per interval (`start` to `end`: hours, or dates with times on one day) in its `row`, coloured by
    `color_by` (the legend lists its values; else by `group`), `label` inside the bar where it fits. `inner` names
    the start and end columns of an inner interval, drawn as a darker band along the bar's lower edge. `group`
    draws the rows as blocks (places, doctors, nurses), the name once in its colour. `assign="first_free"` turns
    a list of tasks into rows of people: within each group, each task goes to the first person free at its start.
    `hours`, `spans`, `into` and `panel` work as in `lanes()`."""
    if assign not in ASSIGN:
        raise ValueError(f"hairline: swimlanes: assign {assign!r} must be 'first_free' or None")
    if row is None and assign is None:
        raise ValueError("hairline: swimlanes: give row=, or assign='first_free' to make rows of people")
    columns = [start, end, *(inner or ())]
    check_columns(data, [row, label, color_by, group, *columns])
    if inner is not None and len(inner) != 2:
        raise ValueError(f"hairline: swimlanes: inner takes (start, end) columns; got {inner!r}")
    times = day_hours(data, columns, inner or ())
    if (times[end] < times[start]).any():
        position = int(np.flatnonzero(times[end] < times[start])[0])
        raise ValueError(f"hairline: swimlanes: row {position + 1} ends before it starts")
    data = data.assign(_row=assigned_rows(data, group, times, start, end) if assign else data[row].astype(str))
    check_labels(data, [column for column in (group, color_by) if column], "swimlanes")
    rows = ordered_names(data["_row"], order, "swimlanes", row or "row")
    if group:
        owner = data.groupby("_row", sort=False)[group].first().astype(str)
        blocks = list(dict.fromkeys(owner[name] for name in rows))
        rows = [name for block in blocks for name in rows if owner[name] == block]
        groups = [owner[name] for name in rows]
    else:
        groups = None
    coloured = color_by or group
    names = list(dict.fromkeys(data[coloured].astype(str))) if coloured else []
    with entities.chart(names, colors, dimension) as palette:
        palette = dict(palette)
    blocks, ys, _ = row_layout(rows, groups, palette if group and not color_by else {}, lone_color())
    if color_by and group:
        # Colour already means `color_by`: the block names stay in ink.
        blocks = [(name, current_settings().neutral["ink"], labels) for name, _, labels in blocks]

    def make() -> HairlineFigure:
        made = figure(title or f"{humanise(row or 'tasks')} over the day", subtitle=subtitle, caption=caption,
                      size=size, height_mm=40)
        made.min_plot = len(rows) * load_tokens()["swimlanes"]["row_pitch"]
        return made
    result, (index,) = target_panels(into, panel, 1, make)
    draw_bars(result, index, data, times, ys, palette, {"start": start, "end": end, "inner": inner,
                                                         "label": label, "colour": coloured})
    ax = result.axes[index]
    if groups:
        separators(ax, blocks, load_tokens()["reference"]["width"] * result.settings.base_size,
                   result.settings.neutral["axis"])
        result.row_blocks(index, blocks)
    else:
        result.categories(index, list(reversed(rows)), "y")
    ax.set_ylim(-0.5, len(rows) - 0.5)
    ax.update_datalim([(float(times[start].min()), 0), (float(times[end].max()), 0)])
    result.time_axis(index, hours, spans)
    add_legend(result, [("square", palette[name], name) for name in names] if color_by else [])
    return result


def draw_bars(result: HairlineFigure, index: int, data: pd.DataFrame, times: dict[str, np.ndarray],
              ys: dict[str, float], palette: dict[str, str], options: dict) -> None:
    """Bars with a surface gap between neighbours, the inner band, the label (shown where it fits) and a tooltip."""
    ax, settings, rules = result.axes[index], current_settings(), load_tokens()["swimlanes"]
    half, size = rules["bar"] / 2, role_size(settings, "label")
    for position, (_, record) in enumerate(data.iterrows()):
        low, high, y = times[options["start"]][position], times[options["end"]][position], ys[record["_row"]]
        color = palette.get(str(record[options["colour"]]), lone_color()) if options["colour"] else lone_color()
        ax.add_patch(Rectangle((low, y - half), high - low, 2 * half, facecolor=color, edgecolor=settings.neutral[
            "surface"], linewidth=rules["gap_pt"], zorder=2))
        if options["inner"]:
            inside = [times[column][position] for column in options["inner"]]
            if all(np.isfinite(inside)):
                # Along the bar's lower edge, so the label above it stays on the bar's own colour.
                ax.add_patch(Rectangle((inside[0], y - half), inside[1] - inside[0], rules["inner"] * 2 * half,
                                       facecolor=darker(color), edgecolor="none", linewidth=0, zorder=3))
        name = str(record[options["label"]]) if options["label"] else ""
        if name:
            artist = ax.text((low + high) / 2, y, name, ha="center", va="center", fontsize=size, zorder=4,
                             color=text_color(color, {"neutral": settings.neutral}),
                             fontfamily=families(settings.font), gid=STATIC_ID)
            result.inside_labels.append((index, artist, low, high))
        text = f"{name + ' · ' if name else ''}{record['_row']}: {clock(low)}–{clock(high)}"
        result.hover(index, record["_row"], color, (low, y - half, high, y + half), text)
