"""Bar chart: counts or sums per category, side by side or stacked, vertical or horizontal, values at the ends."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import pandas as pd
from matplotlib.patches import Rectangle

from hairline import entities
from hairline.charts.common import (
    check_columns,
    check_labels,
    check_numeric,
    check_present,
    coarse_groups,
    group_names,
    humanise,
    labels_with_n,
    ordered_names,
    partial_caption,
    with_caption,
    with_counts,
)
from hairline.charts.correlation_geometry import text_color
from hairline.charts.timeseries import groups_of
from hairline.drawing import measure_for
from hairline.figure import MM_PER_INCH, HairlineFigure, figure, size_settings
from hairline.fonts import families
from hairline.marks import STATIC_ID, context_color, lone_color
from hairline.numbers import auto_digits, format_compact, format_number, format_percent, number_unit, word
from hairline.palettes import interpolate, ramp
from hairline.settings import current_settings, role_size
from hairline.tokens import load_tokens

SCALES = ("free", "shared")
HEADERS = ("total", "n")
SHOW_N = (False, True, "column")
INSIDE = (None, "name")


def bar_table(data: pd.DataFrame, category: str, value: str, by: str | None, order: Sequence[str] | None,
              sort: str, groups: list[str] | None = None) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Sums per category (and group), the category order and the group order (`groups` given: the order of every
    facet). A cell whose values are all missing stays missing (no bar, label or tooltip); for sorting and percent
    totals it counts as zero."""
    columns = list(dict.fromkeys([category] + ([by] if by else [])))
    check_labels(data, columns, "bars")
    check_present(data, value, "bars")
    check_numeric(data, [value], "bars")
    names = ordered_names(data[category], order or None, "bars", category)
    groups = groups if groups is not None else group_names(data[by]) if by else [""]
    table = data.groupby(columns, sort=False, observed=True)[value].sum(min_count=1).reset_index()
    table[category] = table[category].astype(str)
    if by:
        table[by] = table[by].astype(str)
    if sort == "value" and not order:
        totals = table.groupby(category, sort=False)[value].sum()
        names = sorted(names, key=lambda name: -totals[name])
    return table, names, groups


def fold_top(table: pd.DataFrame, names: list[str], top: int | None, other: str, category: str, value: str,
             by: str | None) -> tuple[pd.DataFrame, list[str]]:
    """The `top` largest categories (by their totals) keep their order; the rest sum into one bar named `other`,
    drawn last. A category already named `other` joins the rest."""
    if top is None or len(names) <= top:
        return table, names
    totals = table.groupby(category, sort=False)[value].sum()
    ranked = sorted(names, key=lambda name: (-float(totals.get(name, 0.0)), names.index(name)))[:top]
    kept = [name for name in names if name in ranked and name != other]
    folded = table.assign(**{category: table[category].where(table[category].isin(kept), other)})
    columns = list(dict.fromkeys([category] + ([by] if by else [])))
    folded = folded.groupby(columns, sort=False)[value].sum(min_count=1).reset_index()
    return folded, kept + [other]


def check_top(top: object, scales: str, partial: Mapping | None, names: Sequence[str]) -> None:
    if top is not None and (isinstance(top, bool) or not isinstance(top, int) or top < 1):
        raise ValueError(f"hairline: bars: top must be a whole number of 1 or more; got {top!r}")
    if scales not in SCALES:
        raise ValueError(f"hairline: bars: scales {scales!r} must be one of {', '.join(SCALES)}")
    unknown = [str(name) for name in (partial or {}) if str(name) not in names]
    if unknown:
        raise ValueError(f"hairline: bars: partial names {unknown[0]!r}, which is not a category; categories: "
                         f"{', '.join(names)}")


def is_long(names: Sequence[str]) -> bool:
    rules = load_tokens()["bars"]
    return len(names) > rules["horizontal_count"] or max(len(name) for name in names) > rules["horizontal_length"]


def fits_upright(names: Sequence[str], values: Sequence[str], bars_per_slot: int, width_pt: float,
                 settings) -> bool:
    """Upright bars need every category name, and every value over its bar, to fit the room a category gets across
    the plot (the figure's width less its margins and the y labels, about as wide as the widest value), with
    `bars.label_space` x the base size between neighbours; otherwise the bars lie down."""
    rules, spacing, base, measure = load_tokens()["bars"], load_tokens()["spacing"], settings.base_size, \
        measure_for(settings)
    widest = max((measure(text, "label") for text in values), default=0.0)
    plot = width_pt - 2 * spacing["margin"] * base - widest - spacing["y_labels_plot"] * base
    slot = plot / (len(names) - 1 + 2 * rules["category_pad"])
    space = rules["label_space"] * base
    return max(measure(name, "label") for name in names) <= slot - space and widest <= slot / bars_per_slot - space


def upright_values(table: pd.DataFrame, category: str, value: str, by: str | None, names: list[str],
                   groups: list[str], options: dict) -> list[str]:
    """The value texts upright bars would carry over their ends: every bar's, or each stack's total."""
    if not options["labels"] or (options["stacked"] and options["percent"]):
        return []
    heights = [bar_values(table, category, value, by, names, group, options["divide"]) for group in groups]
    numbers = bar_numbers(table, category, value, by, names, groups, options)
    if options["stacked"]:
        heights = [[sum(without_missing(list(column))) for column in zip(*heights, strict=True)]]
    return [value_text(height, options["percent"], numbers) for row in heights for height in row
            if not math.isnan(height)]


def bar_numbers(table: pd.DataFrame, category: str, value: str, by: str | None, names: list[str], groups: list[str],
                options: dict) -> tuple[int, tuple[float, str] | None]:
    """Decimals and unit of the values on the bars: the data's own decimals, or, from 10^9 on, one short-scale
    unit for the chart (1.2 tn, 0.8 tn) with `numbers.compact_digits` decimals."""
    heights = [height for group in groups for height in bar_values(table, category, value, by, names, group, False)]
    if options["stacked"]:
        heights += list(table.groupby(category)[value].sum())
    unit = number_unit(heights, current_settings().locale)
    return (load_tokens()["numbers"]["compact_digits"], unit) if unit else \
        (auto_digits(table[value].to_numpy(dtype=float)), None)


def is_horizontal(panels: list[dict], groups: list[str], options: dict, width: float, columns: int,
                  settings) -> bool:
    """Many or long labels (as drawn, with their n) lie down, and so do labels too wide for upright bars at this
    figure's width (shared by the panel columns); one decision for every panel of the figure."""
    if any(is_long(panel["labels"]) for panel in panels):
        return True
    per_slot = 1 if options["stacked"] else len(groups)
    return not all(fits_upright(panel["labels"], upright_values(panel["table"], options["category"], options["value"],
                                                                options["by"], panel["names"], groups, options),
                                per_slot, width / columns, settings) for panel in panels)


def bar_values(table: pd.DataFrame, category: str, value: str, by: str | None, names: list[str], group: str,
               percent: bool) -> list[float]:
    rows = table if not by else table[table[by].astype(str) == group]
    totals = table.groupby(category)[value].sum()
    if percent:
        check_percent_values(table, category, value)
        check_percent_totals(totals, names)
    sums = rows.groupby(category)[value].sum(min_count=1)
    return [float(sums.get(name, 0.0)) / (float(totals[name]) if percent else 1.0) for name in names]


def without_missing(heights: list[float]) -> list[float]:
    """Heights for stacking and reach: a missing bar takes no room."""
    return [0.0 if math.isnan(height) else height for height in heights]


def check_percent_values(table: pd.DataFrame, category: str, value: str) -> None:
    """Shares are parts of a whole: a negative part would draw below zero and push the others past 100 %."""
    negative = table[table[value] < 0]
    if len(negative):
        raise ValueError(f"hairline: bars: percent needs values of zero or more; {negative.iloc[0][category]!r} has "
                         f"{negative.iloc[0][value]:g}")


def check_percent_totals(totals: pd.Series, names: list[str]) -> None:
    empty = [name for name in names if not totals.get(name, 0.0) > 0]
    if empty:
        raise ValueError(f"hairline: bars: percent needs a total above zero in every category; {empty[0]!r} totals "
                         f"{totals.get(empty[0], 0.0):g}, so its shares are undefined")


def value_text(value: float, percent: bool, numbers: tuple[int, tuple[float, str] | None] = (0, None)) -> str:
    """A bar's value: whole percentages, or the data's own decimals (0.12 stays 0.12, counts stay whole), in the
    chart's unit when its numbers are that large (see bar_numbers)."""
    locale = current_settings().locale
    return format_percent(value, 0, locale) if percent else format_compact(value, *numbers, locale)


def value_label(ax, value: float, position: tuple[float, float], horizontal: bool, percent: bool,
                gid: str = "hairline-value", numbers: tuple = (0, None)) -> None:
    settings = current_settings()
    gap = load_tokens()["bars"]["label_gap"] * role_size(settings, "label")
    ax.annotate(value_text(value, percent, numbers), xy=position, xytext=(gap, 0) if horizontal else (0, gap),
                textcoords="offset points", ha="left" if horizontal else "center",
                va="center" if horizontal else "bottom", fontsize=role_size(settings, "label"),
                color=settings.neutral["muted"], fontfamily=families(settings.font), annotation_clip=False, gid=gid)


def segment_label(ax, value: float, centre: tuple[float, float], color: str, percent: bool,
                  numbers: tuple = (0, None)) -> None:
    """The segment's value in its middle, in ink or surface, whichever contrasts more with the fill."""
    settings = current_settings()
    ax.text(*centre, value_text(value, percent, numbers), ha="center", va="center",
            fontsize=role_size(settings, "label"), color=text_color(color, {"neutral": settings.neutral}),
            fontfamily=families(settings.font), gid="hairline-segment")


def stacked_labels(ax, spots: list[float], base: list[float], heights: list[float], color: str, options: dict) -> None:
    smallest = load_tokens()["bars"]["segment_min"] * options["largest"]
    for spot, low, height in zip(spots, base, heights, strict=True):
        if height >= smallest and height > 0:
            middle = low + height / 2
            segment_label(ax, height, (middle, spot) if options["horizontal"] else (spot, middle), color,
                          options["percent"], options["numbers"])


def draw_bars(ax, table: pd.DataFrame, names: list[str], groups: list[str], options: dict) -> None:
    category, value, by = options["category"], options["value"], options["by"]
    rules, horizontal, stacked = load_tokens()["bars"], options["horizontal"], options["stacked"]
    positions = [len(names) - 1 - index if horizontal else index for index in range(len(names))]
    single = rules["width"] if stacked else rules["width"] / len(groups)
    ups, downs = [0.0] * len(names), [0.0] * len(names)
    edge = {"edgecolor": current_settings().neutral["surface"], "linewidth": rules["gap_pt"] / 2} if stacked else \
        {"linewidth": 0}
    options = {**options, "largest": max_total(table, category, value, by, names, groups, options),
               "numbers": bar_numbers(table, category, value, by, names, groups, options)}
    ends, present = 0.0, [False] * len(names)
    for index, group in enumerate(groups):
        heights = bar_values(table, category, value, by, names, group, options["divide"])
        step = (len(groups) - 1) / 2 - index if horizontal else index - (len(groups) - 1) / 2
        offset = 0.0 if stacked else step * single
        color = options["palette"][group] if by else lone_color()
        where = [position + offset for position in positions]
        draw = ax.barh if horizontal else ax.bar
        base = [up if height >= 0 else down for up, down, height in zip(ups, downs, heights, strict=True)] \
            if stacked else [0.0] * len(names)
        container = draw(where, heights, single * 0.92, base, color=color,
                         label=options["series"][group] if by else "_nolegend_", **edge)
        lighten_partial(container, names, options["partial"])
        recede(container, names, options["context"])
        ends = max([ends, *without_missing(heights)])
        present = [shown or not math.isnan(height) for shown, height in zip(present, heights, strict=True)]
        if stacked and options["labels"]:
            stacked_labels(ax, where, base, heights, color, options)
        elif options["labels"]:
            for spot, height in zip(where, heights, strict=True):
                if not math.isnan(height):
                    value_label(ax, height, (height, spot) if horizontal else (spot, height), horizontal,
                                options["percent"], numbers=options["numbers"])
        ups = [up + max(height, 0.0) for up, height in zip(ups, without_missing(heights), strict=True)]
        downs = [down + min(height, 0.0) for down, height in zip(downs, without_missing(heights), strict=True)]
    if stacked and options["labels"] and not options["percent"]:
        shown = [index for index, value in enumerate(present) if value]
        stacked_totals(ax, [positions[index] for index in shown], [ups[index] for index in shown],
                       [downs[index] for index in shown], horizontal, options["numbers"])
    if options["labels"] and not (stacked and options["percent"]):
        reach = (max(ups) if stacked else ends) * (1 + rules["label_headroom"])
        if options["percent"] and not options["divide"]:
            # Shares of respondents end at 100 %; a label past it may run into the margin.
            reach = min(reach, 1.0)
        ax.update_datalim([(reach, positions[0])] if horizontal else [(positions[0], reach)])


def lighten_partial(container, names: list[str], partial: Sequence[str]) -> None:
    """Bars of incomplete periods (two months of a year) are drawn lighter, so they are not read as a drop."""
    opacity = load_tokens()["partial"]["opacity"]
    for patch, name in zip(container.patches, names, strict=True):
        if name in partial:
            patch.set_alpha(opacity)


def recede(container, names: list[str], context: Sequence[str]) -> None:
    """Categories named as context (an exclusive "none" answer) are drawn in the context grey, outside the ranking's
    colour."""
    for patch, name in zip(container.patches, names, strict=True):
        if name in context:
            patch.set_facecolor(context_color())


def stacked_totals(ax, positions: list[float], ups: list[float], downs: list[float], horizontal: bool,
                   numbers: tuple) -> None:
    """The signed total at the end of the stack: past the positive segments, or the negative ones if none is
    positive. Negative segments stack below zero, positive ones above."""
    for spot, up, down in zip(positions, ups, downs, strict=True):
        end = up if up > 0 else down
        value_label(ax, up + down, (end, spot) if horizontal else (spot, end), horizontal, False, "hairline-total",
                    numbers)


def max_total(table: pd.DataFrame, category: str, value: str, by: str | None, names: list[str], groups: list[str],
              options: dict) -> float:
    if options["percent"]:
        return 1.0
    if options["stacked"]:
        return float(table[value].clip(lower=0).groupby(table[category]).sum().max())
    return float(table[value].max())


def category_n(table: pd.DataFrame, category: str, value: str, names: list[str]) -> dict[str, float]:
    """Each category's total across the groups: the n a share chart would otherwise lose."""
    totals = table.groupby(category, sort=False)[value].sum()
    return {name: float(totals.get(name, 0.0)) for name in names}


def bar_sharing(scales: str, horizontal: bool) -> tuple[bool, bool]:
    """Facets share the value axis when `scales` is shared; the category axis is each panel's own."""
    shared = scales == "shared"
    return (shared, False) if horizontal else (False, shared)


def facet_panels(frames: list[tuple[str, pd.DataFrame]], options: dict, order: Sequence[str] | None, sort: str,
                 groups: list[str]) -> list[dict]:
    """Per facet: its table (the smallest categories folded into `other`), category order and n per category."""
    category, value, by = options["category"], options["value"], options["by"]
    panels = []
    for name, rows in frames:
        table, names, _ = bar_table(rows, category, value, by, order, sort, groups)
        table, names = fold_top(table, names, options["top"], options["other"], category, value, by)
        if sort == "value":
            # An answer outside the ranking (an exclusive "none") goes last.
            names = [name for name in names if name not in options["context"]] + \
                [name for name in names if name in options["context"]]
        panels.append({"name": name, "table": table, "names": names, "n": category_n(table, category, value, names),
                       "total": float(table[value].sum())})
    return panels


def respondent_shares(data: pd.DataFrame, category: str, facet: str | None,
                      respondents: str) -> tuple[pd.DataFrame, dict[str, int]]:
    """Multiple choice: each respondent once per answer, as a share of the respondents of the panel (not of the
    answers, which add up to more than 100 %); and the respondents per panel."""
    check_columns(data, [respondents])
    keys = [column for column in (facet, category) if column]
    check_labels(data, keys, "bars")
    distinct = data.dropna(subset=[respondents]).drop_duplicates(subset=[respondents, *keys])
    labels = distinct[facet].astype(str) if facet else pd.Series([""] * len(distinct), index=distinct.index)
    totals = distinct.groupby(labels, sort=False)[respondents].nunique()
    shares = distinct.groupby(keys, sort=False).size().reset_index(name="_answers")
    panels = shares[facet].astype(str) if facet else pd.Series([""] * len(shares), index=shares.index)
    shares["_share"] = shares["_answers"] / panels.map(totals).to_numpy(dtype=float)
    return shares, {str(name): int(count) for name, count in totals.items()}


def check_survey_options(show_n: object, header: str, inside: str | None, context: Sequence[str],
                         respondents: str | None, options: dict) -> None:
    if show_n not in SHOW_N:
        raise ValueError(f"hairline: bars: show_n {show_n!r} must be True, False or 'column'")
    if header not in HEADERS:
        raise ValueError(f"hairline: bars: header {header!r} must be one of {', '.join(HEADERS)}")
    if inside not in INSIDE:
        raise ValueError(f"hairline: bars: inside {inside!r} must be 'name' or None")
    if inside and not (options["by"] and options["stacked"]):
        raise ValueError("hairline: bars: inside='name' writes the names of stacked groups; give by= and stacked=True")
    if context and options["by"]:
        raise ValueError("hairline: bars: context greys categories of a single series; with by=, use colors=")
    if respondents and (options["by"] or options["percent"] or options["value_given"]):
        raise ValueError("hairline: bars: respondents counts one answer per row; leave out value, by, percent "
                         "and normalize")


def bars(data: pd.DataFrame, category: str, value: str | None = None, by: str | None = None, *,
         title: str | None = None, subtitle: str | None = None, caption: str | None = None, stacked: bool = False,
         percent: bool = False, horizontal: bool | None = None, sort: str | None = None,
         order: Sequence[str] | None = None, labels: bool = True, colors: Mapping[str, str] | None = None,
         size: str = "onehalf", facet: str | None = None, scales: str = "free", columns: int | None = None,
         top: int | None = None, other: str | None = None, partial: Mapping[str, str] | None = None,
         show_n: bool | str = False, normalize: bool = False, color_by: str | None = None,
         dimension: str | None = None, context: Sequence[str] | None = None, header: str = "total",
         inside: str | None = None, respondents: str | None = None) -> HairlineFigure:
    """Bars per category; without `value` rows are counted. Long or many labels, or labels too wide for upright
    bars at the figure's width, turn the bars horizontal; single series are sorted by value unless `order` or
    `sort="given"` says otherwise.

    `facet` draws one panel per value of that column, each with its own value axis (`scales="free"`) or one shared
    axis, in `columns` columns, the facet's name and total in its panel header. `top` keeps the n largest
    categories per panel and folds the rest into one bar named `other` (the locale's "Other"). `partial` names
    incomplete periods and what they hold ({"2021": "2 months"}): their bars are drawn lighter and the caption
    says so. `show_n` writes each category's n after its label; `normalize` draws shares of each category's total
    (as `percent`) and keeps the n in the labels. `color_by` colours the groups of `by` by a coarser column, with
    that column's values in the legend; `dimension` keeps their colours off the slots another dimension holds.

    For surveys: `respondents` names the respondent column of multiple-choice answers (one row per answer): each
    respondent counts once per answer, as a share of the panel's respondents, and the caption says several answers
    were possible. `context` names categories drawn in the context grey (an exclusive "none" answer), last when
    sorted by value. `header="n"` puts each facet's n in its header instead of its total. `show_n="column"`
    writes each bar's n in a column right of the panel. `inside="name"` writes each stacked segment's name and
    value inside it, in greys by position, so rows may hold different answers and no legend is needed."""
    value_given = value is not None
    context = [str(name) for name in (context or ())]
    respondent_n: dict[str, int] = {}
    if respondents is not None:
        if value_given or by or percent or normalize:
            check_survey_options(show_n, header, inside, context, respondents,
                                 {"by": by, "stacked": stacked, "percent": percent or normalize,
                                  "value_given": value_given})
        data, respondent_n = respondent_shares(data, category, facet, respondents)
        value = "_share"
    data, value = with_counts(data, value)
    check_columns(data, [category, value, by, facet, color_by])
    stacked = stacked and by is not None
    percent = percent or normalize
    show_n = "column" if show_n == "column" else bool(show_n or normalize)
    if (sort or "value") not in ("value", "given"):
        raise ValueError(f"hairline: bars: sort {sort!r} must be 'value' or 'given'")
    if color_by is not None and by is None:
        raise ValueError("hairline: bars: color_by needs by=, the groups it colours")
    sort = sort or ("given" if by and not stacked else "value")
    check_labels(data, [column for column in (by, facet) if column], "bars")
    groups = group_names(data[by]) if by else [""]
    frames = groups_of(data, facet, None, "bars")
    locale = current_settings().locale
    options = {"category": category, "value": value, "by": by, "stacked": stacked,
               "percent": percent or respondents is not None, "divide": percent, "labels": labels, "top": top,
               "other": other or word("other", locale), "partial": [], "context": context, "inside": inside,
               "header": header, "value_given": value_given, "respondent_n": respondent_n}
    check_survey_options(show_n, header, inside, context, None, options)
    panels = facet_panels(frames, options, order, sort, groups)
    every_name = list(dict.fromkeys(name for panel in panels for name in panel["names"]))
    check_top(top, scales, partial, every_name)
    unknown = [name for name in context if name not in every_name]
    if unknown:
        raise ValueError(f"hairline: bars: context names {unknown[0]!r}, which is not a category; categories: "
                         f"{', '.join(every_name)}")
    options["partial"] = [str(name) for name in (partial or {})]
    coarse = coarse_groups(data, by, color_by, "bars") if color_by else None
    series = {group: coarse[group] if coarse else group for group in groups}
    width_mm, _, settings = size_settings(size, None, None)
    width = width_mm / MM_PER_INCH * 72
    columns = columns or (min(len(panels), 2) if facet else 1)
    for panel in panels:
        panel["labels"] = labels_with_n(panel["names"], panel["n"], locale) if show_n is True else panel["names"]
    if (show_n == "column" or inside) and horizontal is False:
        raise ValueError("hairline: bars: show_n='column' and inside='name' need horizontal bars")
    if show_n == "column" or inside:
        horizontal = True
    if horizontal is None:
        horizontal = is_horizontal(panels, groups, options, width, columns, settings)
    options["show_n"] = show_n
    sharex, sharey = bar_sharing(scales, horizontal) if facet else (False, False)
    split = f" and {str(by).replace('_', ' ')}" if by and by != category else ""
    result = figure(title or f"{humanise(value)} by {str(category).replace('_', ' ')}{split}", subtitle=subtitle,
                    caption=with_caption(caption, partial_caption(partial, locale),
                                         word("several_answers", locale) if respondents else None),
                    size=size, panels=len(panels),
                    layout="grid" if facet else "rows", columns=columns, sharex=sharex, sharey=sharey)
    with entities.chart(list(dict.fromkeys(series.values())) if by else [], colors, dimension) as palette:
        options.update(palette={group: palette[series[group]] for group in groups} if by else {}, series=series,
                       horizontal=horizontal)
        for index, panel in enumerate(panels):
            draw_panel(result, index, panel, groups, options, facet, locale)
    if inside:
        result.legend([])
    elif by:
        result.legend()
    return result


def draw_panel(result: HairlineFigure, index: int, panel: dict, groups: list[str], options: dict, facet: str | None,
               locale: str) -> None:
    ax, names, horizontal = result.axes[index], panel["names"], options["horizontal"]
    if options["inside"]:
        draw_named(result, index, panel, options)
    else:
        draw_bars(ax, panel["table"], names, groups, options)
    if options["show_n"] == "column":
        result.numbers_column(index, [(len(names) - 1 - position, "n", format_number(panel["n"][name], 0, locale))
                                      for position, name in enumerate(names)])
    labels = panel["labels"]
    result.categories(index, list(reversed(labels)) if horizontal else labels, "y" if horizontal else "x")
    pad = load_tokens()["bars"]["category_pad"]
    (ax.set_ylim if horizontal else ax.set_xlim)(-pad, len(names) - 1 + pad)
    if options["percent"]:
        result.percent_axis(index, "x" if horizontal else "y")
    if facet:
        result.panel_header(index, panel["name"], stats=[header_stat(panel, options, locale)])


def header_stat(panel: dict, options: dict, locale: str) -> tuple[str, str]:
    """A facet's total, or its n: the respondents of a multiple-choice panel, else its total count."""
    if options["header"] == "n":
        count = options["respondent_n"].get(panel["name"], panel["total"])
        return "n", format_number(count, 0, locale)
    return word("total", locale), format_number(panel["total"], auto_digits([panel["total"]]), locale)


def named_colors(count: int) -> list[str]:
    """Greys from dark to light, one per position in a row, the near-white step left out."""
    return list(reversed(interpolate(ramp("greys"), count + 1)))[:count]


def draw_named(result: HairlineFigure, index: int, panel: dict, options: dict) -> None:
    """Stacked rows whose groups differ per row, each segment named inside where it fits, in greys by position
    (first answer darkest), each a tooltip target; no legend is needed."""
    ax, category, value, by = result.axes[index], options["category"], options["value"], options["by"]
    rules, settings, names, table = load_tokens()["bars"], current_settings(), panel["names"], panel["table"]
    half = rules["width"] * 0.92 / 2
    rows = {name: table[table[category] == name] for name in names}
    colors = named_colors(max(len(found) for found in rows.values()))
    for position, name in enumerate(names):
        y, start, found = len(names) - 1 - position, 0.0, rows[name]
        total = float(found[value].sum())
        for slot, (group, amount) in enumerate(zip(found[by].astype(str), found[value].astype(float), strict=True)):
            if not amount > 0:
                continue
            width = amount / total if options["divide"] else amount
            color, shown = colors[slot], value_text(width, options["percent"], (auto_digits([width]), None))
            ax.add_patch(Rectangle((start, y - half), width, 2 * half, facecolor=color,
                                   edgecolor=settings.neutral["surface"], linewidth=rules["gap_pt"] / 2))
            artist = ax.text(start + width / 2, y, f"{group} {shown}", ha="center", va="center",
                             fontsize=role_size(settings, "label"), fontfamily=families(settings.font),
                             color=text_color(color, {"neutral": settings.neutral}), gid=STATIC_ID)
            result.inside_labels.append((index, artist, start, start + width))
            result.hover(index, group, color, (start, y - half, start + width, y + half), f"{group}: {name}, {shown}")
            start += width
