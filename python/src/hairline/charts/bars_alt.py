"""The description of a bar chart for its alt text: its highest and lowest bars, as their labels write them. Mirrored
in R's bars_alt.R."""

from __future__ import annotations

import math
from collections.abc import Sequence

import pandas as pd

from hairline.alt_text import described, extremes

# Between the parts of a bar's name: its panel, its category and its group ("Surgery · ICU · 2025"), as the
# captions name a facet's rows.
NAME_PARTS = " · "


def bar_name(parts: Sequence[str]) -> str:
    """A bar's name from its parts, each once (a facet by the groups names them once)."""
    return NAME_PARTS.join(dict.fromkeys(parts))


def bar_amount(rows: pd.DataFrame, value: str) -> float:
    """The sum of the rows' values; missing when none has one."""
    known = rows[value].dropna()
    return float(known.sum()) if len(known) else math.nan


def panel_entries(panel: dict, groups: Sequence[str], options: dict, faceted: bool,
                  write) -> list[tuple[str, float, str]]:
    """Each bar of a panel as (name, value, value as written), in reading order: category, then group. A stack
    without shares is one bar, its total, as its label above it."""
    category, value, by, table = options["category"], options["value"], options["by"], panel["table"]
    labels = table[category].astype(str)
    members = table[by].astype(str) if by else None
    prefix = [str(panel["name"])] if faceted else []
    entries = []
    for name in panel["names"]:
        rows = table[labels == name]
        if options["stacked"] and not options["divide"]:
            amount = bar_amount(rows, value)
            entries.append((bar_name([*prefix, name]), amount, write(amount, False)))
            continue
        total = bar_amount(rows, value)
        for group in groups:
            cell = rows[members[rows.index] == group] if by else rows
            if not len(cell):
                continue
            amount = bar_amount(cell, value) / (total if options["divide"] else 1.0)
            entries.append((bar_name([*prefix, name, *([group] if by else [])]), amount,
                            write(amount, options["percent"])))
    return entries


def bars_description(panels: list[dict], groups: Sequence[str], options: dict, faceted: bool, numbers,
                     value_text, locale: str) -> str:
    """'Bar chart. Highest: …; lowest: ….' over every panel; `numbers(panel)` gives a panel's decimals and unit,
    `value_text` writes a value as the bar's label does."""
    entries = []
    for panel in panels:
        digits = numbers(panel)
        entries += panel_entries(panel, groups, options, faceted,
                                 lambda amount, percent, digits=digits: value_text(amount, percent, digits))
    return described("kind_bars", extremes(entries, locale), locale)
