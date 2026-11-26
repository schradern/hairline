"""A figure's description from its data, for its alt text: the kind of chart and what stands out, in the figure's
locale ("Bar chart. Highest: ICU (727); lowest: Ward (495)."). Charts write it while they draw; `figure_alt()`
puts it after the title and subtitle, so every file, the HTML figure and the host manifest carry it. Mirrored in
R's alt_text.R: the same words, numbers and order in both packages."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from hairline.numbers import format_number, locale_symbols, word
from hairline.tokens import load_tokens

# Values equal to this many decimals are a tie: shares divided in Python and R may differ in their last bits.
TIE_DIGITS = 9


def named(names: Sequence[str], locale: str | None) -> str:
    """Names joined by commas, at most `alt_text.max_names` of them and how many more."""
    most = load_tokens()["alt_text"]["max_names"]
    shown = ", ".join(names[:most])
    return shown if len(names) <= most else word("more_names", locale, names=shown, n=len(names) - most)


def percent_text(value: float, digits: int, locale: str | None) -> str:
    """A value already in percent (13.0) as the charts write it with its sign ('13.0%', '13,0 %' in de)."""
    return format_number(value, digits, locale) + locale_symbols(locale)["percent_space"] + "%"


# The words extremes() writes: both ends, one value alone, every value the same.
VALUE_WORDS = ("extremes", "one_value", "all_same")
# The same for each group's centre ("Highest median: …"), its name given as the `centre` field.
CENTRE_WORDS = ("centre_extremes", "centre_one", "centre_same")


def extremes(entries: Sequence[tuple[str, float, str]], locale: str | None, words: Sequence[str] = VALUE_WORDS,
             **fields: str) -> str:
    """The highest and lowest of (name, value, value as written) in reading order, ties named together; one value
    on its own, or every value when they are all the same, in `words` with any further `fields`. Missing values
    are left out."""
    known = [(name, round(value, TIE_DIGITS), text) for name, value, text in entries if math.isfinite(value)]
    both, one, same = words
    if not known:
        return ""
    if len(known) == 1:
        return word(one, locale, name=known[0][0], value=known[0][2], **fields)
    high, low = max(value for _, value, _ in known), min(value for _, value, _ in known)
    if high == low:
        return word(same, locale, value=known[0][2], **fields)
    highs = [entry for entry in known if entry[1] == high]
    lows = [entry for entry in known if entry[1] == low]
    return word(both, locale, high=named([name for name, _, _ in highs], locale), high_value=highs[0][2],
                low=named([name for name, _, _ in lows], locale), low_value=lows[0][2], **fields)


def grid_extremes(grid: np.ndarray, tips: dict, titles: dict[str, str], locale: str | None) -> str:
    """Where a grid (rows y, columns x) is highest and lowest, as its tooltips name the point: the first such point
    reading row by row."""
    known = np.isfinite(grid)
    high, low = float(np.max(grid[known])), float(np.min(grid[known]))
    if round(high, TIE_DIGITS) == round(low, TIE_DIGITS):
        row, column = np.argwhere(known)[0]
        return word("all_same", locale, value=tips["z"][row][column])

    def point(value: float) -> tuple[str, str]:
        row, column = np.argwhere(known & (grid == value))[0]
        return (word("grid_point", locale, x_title=titles["x"], x=tips["x"][column], y_title=titles["y"],
                     y=tips["y"][row]), tips["z"][row][column])
    (high_at, high_text), (low_at, low_text) = point(high), point(low)
    return word("grid_extremes", locale, high=high_at, high_value=high_text, low=low_at, low_value=low_text)


def described(kind: str, findings: str, locale: str | None) -> str:
    """The kind of chart (a `kind_*` word) and its findings, or the kind alone when nothing stands out."""
    name = word(kind, locale)
    return word("described", locale, kind=name, findings=findings) if findings else f"{name}."
