"""Venn diagram: two or three sets, the count of every region, from named sets or membership columns."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from itertools import combinations

import pandas as pd

from hairline import entities
from hairline.charts.common import check_columns, humanise, joined
from hairline.charts.venn_geometry import venn_drawing
from hairline.figure import HairlineFigure, figure
from hairline.numbers import format_number
from hairline.settings import current_settings


def check_count(names: list[str], proportional: bool) -> None:
    count = len(names)
    if count > 3:
        raise ValueError(f"hairline: venn: {count} sets given ({', '.join(names)}); at most 3 fit — show the "
                         "intersections as bars instead")
    if count < 2:
        raise ValueError(f"hairline: venn: {count} set given ({', '.join(names)}); a Venn diagram needs 2 or 3")
    if proportional and count != 2:
        raise ValueError(f"hairline: venn: proportional areas need two sets; {count} given")


def column_codes(data: pd.DataFrame, columns: Sequence[str]) -> list[int]:
    """Per row, the sets it belongs to as bits (first column = 1)."""
    check_columns(data, list(columns))
    codes = [0] * len(data)
    for bit, column in enumerate(columns):
        for row, value in enumerate(data[column].tolist()):
            if isinstance(value, str) or value not in (0, 1):
                raise ValueError(f"hairline: venn: column '{column}' needs TRUE/FALSE or 0/1 values; "
                                 f"found {value!r}")
            codes[row] += (1 << bit) if value else 0
    return codes


def member_codes(sets: Mapping[str, Iterable]) -> list[int]:
    """Per member of any set, the sets it belongs to as bits (first set = 1). Each set is read once, so iterators
    and generators count like lists."""
    listed = [list(values) for values in sets.values()]
    groups = [set(values) for values in listed]
    members = dict.fromkeys(member for values in listed for member in values)
    return [sum(1 << bit for bit, group in enumerate(groups) if member in group) for member in members]


def venn_spec(data: Mapping[str, Iterable] | pd.DataFrame, columns: Sequence[str] | None = None, *,
              colors: Mapping[str, str] | None = None, proportional: bool = False) -> dict:
    """Sets with their sizes and colours by count, and every region (each combination of sets) with its count."""
    if isinstance(data, pd.DataFrame):
        if not columns:
            raise ValueError("hairline: venn: name the membership columns, e.g. columns=['diabetes', 'obesity']")
        names, codes = [humanise(column) for column in columns], column_codes(data, columns)
    else:
        names, codes = [str(name) for name in data], member_codes(data)
    check_count(names, proportional)
    counts, locale, palette = Counter(codes), current_settings().locale, entities.colors_for(names, colors)
    sets = []
    for bit, name in enumerate(names):
        size = sum(count for code, count in counts.items() if code & (1 << bit))
        sets.append({"name": name, "value": size, "value_text": format_number(size, 0, locale),
                     "color": palette[name]})
    regions = []
    for size in range(1, len(names) + 1):
        for members in combinations(range(len(names)), size):
            count = counts.get(sum(1 << bit for bit in members), 0)
            regions.append({"sets": list(members), "value": count, "value_text": format_number(count, 0, locale)})
    if proportional and not all(entry["value"] for entry in sets):
        raise ValueError("hairline: venn: proportional areas need every set to have members")
    return {"sets": sets, "regions": regions, "proportional": proportional}


def venn(data: Mapping[str, Iterable] | pd.DataFrame, columns: Sequence[str] | None = None, *,
         title: str | None = None, subtitle: str | None = None, caption: str | None = None,
         colors: Mapping[str, str] | None = None, proportional: bool = False, size: str = "onehalf") -> HairlineFigure:
    """Overlap of two or three sets: named sets ({name: members}) or membership columns (one row per member)."""
    spec = venn_spec(data, columns, colors=colors, proportional=proportional)
    label = joined(list(columns) if isinstance(data, pd.DataFrame) else [entry["name"] for entry in spec["sets"]])
    result = figure(title or f"Overlap of {label}", subtitle=subtitle, caption=caption, size=size)
    result.draw(0, lambda box, measure, style: venn_drawing(spec, box, measure, style))
    return result
