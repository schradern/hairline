"""Diverging bars for rating scales: per item the share of each rating, stacked away from the split between
disagreement and agreement (a middle level centred on it), the levels collapsed into a few named bins that a reader
can tell apart, negatively worded items recoded, sections as blocks, and median [IQR] and n beside each row."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from hairline.charts.common import (
    check_columns,
    check_labels,
    check_numeric,
    coarse_groups,
    humanise,
    ordered_names,
    with_caption,
    without_small_categories,
)
from hairline.charts.likert_geometry import likert_drawing
from hairline.charts.spread import level_number, spread_axis
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.numbers import format_number, word
from hairline.palettes import default_ramp, interpolate, ramp
from hairline.stats.density import level_quantiles
from hairline.tokens import load_tokens

STATS = ("median", "iqr", "n")
SORTS = (None, "balance")
DASH = "–"


def scale_levels(values: np.ndarray, levels: Sequence[float] | None) -> list[float]:
    """The scale's levels, given or found in the data; a rating off the scale is refused."""
    found = sorted({float(value) for value in values})
    if levels is None:
        return found
    scale = sorted(float(level) for level in levels)
    off = [value for value in found if value not in scale]
    if off:
        raise ValueError(f"hairline: likert: rating {level_number(off[0])} is not a level of the scale "
                         f"({level_number(scale[0])} to {level_number(scale[-1])})")
    return scale


def sides(levels: list[float], split: float | None) -> tuple[list[float], list[float], list[float]]:
    """The levels left of the split, at it (a middle level drawn centred) and right of it. By default the split is
    the middle level of an odd scale, else midway between the two middle levels."""
    if split is None:
        middle = len(levels) // 2
        split = levels[middle] if len(levels) % 2 else (levels[middle - 1] + levels[middle]) / 2
    left = [level for level in levels if level < split]
    right = [level for level in levels if level > split]
    if not left or not right:
        raise ValueError(f"hairline: likert: split {level_number(split)} must leave levels on both sides")
    return left, [level for level in levels if level == split], right


def bin_label(levels: list[float]) -> str:
    first, last = level_number(levels[0]), level_number(levels[-1])
    return first if len(levels) == 1 else f"{first}{DASH}{last}"


def side_bins(levels: list[float], outer_first: bool) -> list[list[float]]:
    """A side's bins: each level its own up to `likert.levels_per_side`, else two, the outer one holding the
    extreme half (1–2 beside 3–5)."""
    if len(levels) <= load_tokens()["likert"]["levels_per_side"]:
        return [[level] for level in levels]
    half = len(levels) // 2
    if outer_first:
        return [levels[:half], levels[half:]]
    return [levels[:len(levels) - half], levels[len(levels) - half:]]


def given_bins(bins: Mapping[str, tuple[float, float]], left: list[float], middle: list[float],
               right: list[float]) -> list[tuple[str, list[float]]]:
    """Bins as named: each a range of levels on one side (or the middle level), every level in exactly one."""
    found, used = [], []
    for name, (low, high) in bins.items():
        levels = [level for level in left + middle + right if low <= level <= high]
        if not levels or not (set(levels) <= set(left) or set(levels) <= set(right) or set(levels) <= set(middle)):
            raise ValueError(f"hairline: likert: bin '{name}' must hold levels of one side of the split")
        used += levels
        found.append((str(name), levels))
    missing = [level for level in left + middle + right if used.count(level) != 1]
    if missing:
        raise ValueError(f"hairline: likert: bins must hold every level once; {level_number(missing[0])} is not")
    return sorted(found, key=lambda entry: entry[1][0])


def scale_bins(levels: list[float], split: float | None, bins: Mapping[str, tuple[float, float]] | None,
               ramp_name: str | None = None) -> list[dict]:
    """Bins left to right with their side ("left", "middle", "right") and colour from the diverging ramp, the
    middle colour for a middle level. The high half takes the ramp's first pole (blue on the default ramp): agreement
    reads cool, disagreement warm."""
    left, middle, right = sides(levels, split)
    named = given_bins(bins, left, middle, right) if bins else \
        [(bin_label(group), group) for group in side_bins(left, True) + ([middle] if middle else []) +
         side_bins(right, False)]
    lefts = [entry for entry in named if entry[1][0] in left]
    rights = [entry for entry in named if entry[1][0] in right]
    reach = max(len(lefts), len(rights))
    colors = list(reversed(interpolate(ramp(ramp_name or default_ramp("diverging")), 2 * reach + 1)))
    found = []
    for index, (name, group) in enumerate(lefts):
        found.append({"name": name, "levels": group, "side": "left", "color": colors[reach - len(lefts) + index]})
    found += [{"name": name, "levels": group, "side": "middle", "color": colors[reach]}
              for name, group in named if group[0] in middle]
    for index, (name, group) in enumerate(rights):
        found.append({"name": name, "levels": group, "side": "right", "color": colors[reach + 1 + index]})
    return found


def stat_pairs(values: np.ndarray, stats: Sequence[str]) -> list[list[str]]:
    """Median, IQR and n on the data's levels, in spread's key-number style."""
    q1, middle, q3 = level_quantiles(values, [0.25, 0.5, 0.75])
    parts = {"median": [word("median"), level_number(middle)],
             "iqr": [word("iqr"), f"{level_number(q1)}{DASH}{level_number(q3)}"],
             "n": ["n", format_number(len(values), 0)]}
    return [parts[name] for name in stats]


def item_rows(data: pd.DataFrame, item: str, rating: str, names: list[str], scale: dict) -> list[dict]:
    """Per item its label, section, n, the share in each bin (in percent) and its key numbers."""
    rows = []
    low, high, reverse = scale["levels"][0], scale["levels"][-1], scale["reverse"]
    for name in names:
        values = data.loc[data[item].astype(str) == name, rating].dropna().astype(float).to_numpy()
        if name in reverse:
            values = low + high - values
        if not len(values):
            continue
        shares = [float(np.isin(values, entry["levels"]).mean()) * 100 for entry in scale["bins"]]
        label = f"{name} ({word('reversed')})" if name in reverse else name
        rows.append({"name": label, "item": name, "section": scale["sections"].get(name), "n": len(values),
                     "shares": shares, "pairs": stat_pairs(values, scale["stats"])})
    return rows


def balance(row: dict, bins: list[dict]) -> float:
    return sum(share * {"left": -1, "middle": 0, "right": 1}[entry["side"]]
               for share, entry in zip(row["shares"], bins, strict=True))


def ordered_rows(rows: list[dict], bins: list[dict], sort: str | None) -> list[dict]:
    """Rows by section (in the order sections first appear), then by agreement less disagreement when sorted."""
    sections = list(dict.fromkeys(row["section"] for row in rows))
    if sort == "balance":
        return sorted(rows, key=lambda row: (sections.index(row["section"]), -balance(row, bins)))
    return sorted(rows, key=lambda row: sections.index(row["section"]))


def reach_axis(rows: list[dict], bins: list[dict]) -> dict:
    """One axis in percent either side of the split, as far as the longer side reaches, labelled outward from 0."""
    def side(row: dict, name: str) -> float:
        return sum(share * (0.5 if entry["side"] == "middle" else 1.0)
                   for share, entry in zip(row["shares"], bins, strict=True) if entry["side"] in (name, "middle"))
    reach = max(max(side(row, "left"), side(row, "right")) for row in rows)
    half = spread_axis([0.0], [reach], False, True)
    breaks = [-value for value in reversed(half["breaks"][1:])] + half["breaks"]
    labels = list(reversed(half["labels"][1:])) + half["labels"]
    return {"breaks": breaks, "labels": labels, "low": -half["high"], "high": half["high"]}


def check_options(stats: Sequence[str], sort: str | None, reverse: Sequence[str], names: list[str]) -> None:
    unknown = [name for name in stats if name not in STATS]
    if unknown:
        raise ValueError(f"hairline: likert: unknown statistic {unknown[0]!r}; use any of {', '.join(STATS)}")
    if sort not in SORTS:
        raise ValueError(f"hairline: likert: sort {sort!r} must be 'balance' or None")
    missing = [str(name) for name in reverse if str(name) not in names]
    if missing:
        raise ValueError(f"hairline: likert: reverse names {missing[0]!r}, which is not an item")


def likert_spec(data: pd.DataFrame, item: str, rating: str, *, levels: Sequence[float] | None = None,
                split: float | None = None, bins: Mapping[str, tuple[float, float]] | None = None,
                group: str | None = None, reverse: Sequence[str] = (), order: Sequence[str] | None = None,
                sort: str | None = None, stats: Sequence[str] = STATS, axis_title: str | None = None,
                ramp_name: str | None = None) -> dict:
    check_columns(data, [item, rating, group])
    check_labels(data, [item], "likert")
    check_numeric(data, [rating], "likert")
    names = ordered_names(data[item], order, "likert", item)
    check_options(stats, sort, reverse, names)
    scale = {"levels": scale_levels(data[rating].dropna().to_numpy(dtype=float), levels), "stats": list(stats),
             "reverse": [str(name) for name in reverse],
             "sections": coarse_groups(data, item, group, "likert") if group else {}}
    scale["bins"] = scale_bins(scale["levels"], split, bins, ramp_name)
    rows = item_rows(data, item, rating, names, scale)
    if not rows:
        raise ValueError(f"hairline: likert: no ratings to draw; '{rating}' is empty or missing in every row")
    rows = ordered_rows(rows, scale["bins"], sort)
    return {"rows": rows, "bins": scale["bins"], "axis": reach_axis(rows, scale["bins"]),
            "axis_title": axis_title if axis_title is not None else word("respondents_share")}


def likert(data: pd.DataFrame, item: str, rating: str, *, levels: Sequence[float] | None = None,
           split: float | None = None, bins: Mapping[str, tuple[float, float]] | None = None,
           group: str | None = None, reverse: Sequence[str] = (), order: Sequence[str] | None = None,
           sort: str | None = None, stats: Sequence[str] = STATS, axis_title: str | None = None,
           key_title: str | None = None, ramp: str | None = None, title: str | None = None,
           subtitle: str | None = None, caption: str | None = None, size: str = "double", min_n: int | None = None,
           x_title: str | None = None) -> HairlineFigure:
    """Ratings per item (one row per answer), as diverging bars: the share of each bin stacked away from the
    split between the low and the high half of the scale, a middle level centred on it. `levels` is the scale
    (by default the ratings found), `split` where it divides (by default its middle). `bins` names ranges of levels
    ({"1–2": (1, 2), "3–5": (3, 5), ...}); by default each side keeps its levels up to `likert.levels_per_side`,
    else two bins, so a ten-point scale reads 1–2, 3–5 | 6–8, 9–10. `reverse` names negatively worded items,
    recoded (low becomes high) and marked, so colour keeps one meaning. `group` draws the items in blocks under
    their section's name; `sort="balance"` orders a block by agreement less disagreement. The median, IQR (on the
    data's levels) and n stand beside each row; the binned key sits in the legend row. `ramp` names a diverging
    ramp; the high half takes its first pole. Shared with the other charts: `min_n` leaves out items with fewer
    ratings and names them; `x_title` is the same as `axis_title`."""
    check_columns(data, [item, rating])
    data, small = without_small_categories(data[data[rating].notna()], item, min_n, "likert") if min_n else (data,
                                                                                                         None)
    spec = likert_spec(data, item, rating, levels=levels, split=split, bins=bins, group=group, reverse=reverse,
                       order=order, sort=sort, stats=stats, axis_title=axis_title or x_title, ramp_name=ramp)
    result = figure(title or f"{humanise(rating)} by {str(item).replace('_', ' ')}", subtitle=subtitle,
                    caption=with_caption(caption, small), size=size)
    result.draw(0, lambda box, measure, style: likert_drawing(spec, box, measure, style))
    count = len(spec["bins"])
    result.legend([])
    result.legend_ramp([entry["color"] for entry in spec["bins"]], [(index + 1) / count for index in range(count)],
                       key_title, labels=[entry["name"] for entry in spec["bins"]])
    return fit_height(result)
