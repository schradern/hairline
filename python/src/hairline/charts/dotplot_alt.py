"""The description of a dot plot for its alt text: the rows with the highest and lowest value, in the plot's digits;
with `summary`, the centre it draws ("Highest median: …"). Mirrored in R's dotplot_alt.R."""

from __future__ import annotations

from collections.abc import Sequence

from hairline.alt_text import CENTRE_WORDS, VALUE_WORDS, described, extremes
from hairline.charts.distribution_alt import FACET_PARTS
from hairline.numbers import format_number, locale_symbols, word


def dot_text(value: float, digits: int, percent: bool, locale: str) -> str:
    """A row's value as its number writes it, with the percent sign the heading gives it where it is a share."""
    text = format_number(value, digits, locale)
    return text + locale_symbols(locale)["percent_space"] + "%" if percent else text


def dotplot_description(names: Sequence[str], blocks: Sequence[str], values: Sequence[float], digits: int,
                        percent: bool, centre: str | None, locale: str) -> str:
    """'Dot plot. Highest: Medical (13.0%); lowest: Cardiac (6.0%).' over the rows as drawn, each named with its
    block where there are blocks ("2025 · Medical"); with a summary, its centre names the values."""
    named = [f"{block}{FACET_PARTS}{name}" for block, name in zip(blocks, names, strict=True)] if blocks else names
    entries = [(name, float(value), dot_text(float(value), digits, percent, locale))
               for name, value in zip(named, values, strict=True)]
    found = extremes(entries, locale, CENTRE_WORDS, centre=word(f"centre_{centre}", locale)) if centre else \
        extremes(entries, locale, VALUE_WORDS)
    return described("kind_dotplot", found, locale)
