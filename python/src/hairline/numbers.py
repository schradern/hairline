"""Locale-aware number formatting shared with the R package."""

from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal, localcontext

from hairline.tokens import load_tokens


def locale_symbols(locale: str | None) -> dict[str, str]:
    tokens = load_tokens()
    if locale is None:
        from hairline.settings import current_locale
        locale = current_locale()
    if locale not in tokens["locales"]:
        known = ", ".join(sorted(tokens["locales"]))
        raise ValueError(f"hairline: unknown locale {locale!r}; available locales: {known}")
    return tokens["locales"][locale]


def group_thousands(integer_part: str, separator: str) -> str:
    groups = []
    while len(integer_part) > 3:
        integer_part, tail = integer_part[:-3], integer_part[-3:]
        groups.insert(0, tail)
    return separator.join([integer_part, *groups])


ROUNDING_TOLERANCE = 1e-9
SIGNIFICANT = 15
MISSING = "–"


def fixed_text(magnitude: float, digits: int) -> str:
    """`magnitude` (zero or more) with `digits` decimals, halves rounded up in decimal. The value is read to the 15
    significant digits a double holds, so float noise beyond them does not decide (8.649999999999999 is 8.65, the
    stored 8.645 is a half) and exact values stay exact at any size (1,000,000,000 and 999,999,999,999.4). Digits
    past the fifteenth read as zeros, as in R and the Python package alike."""
    exact = Decimal(f"{magnitude:.{SIGNIFICANT - 1}e}")
    with localcontext() as context:
        context.prec = max(context.prec, SIGNIFICANT + digits + max(0, exact.adjusted()) + 2)
        return f"{exact.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP):f}"


def format_number(value: float, digits: int = 1, locale: str | None = None) -> str:
    """Format with fixed decimals (halves up), locale separators and a true minus sign (U+2212); a missing value
    reads as an en dash and an infinite one as ∞."""
    symbols = locale_symbols(locale)
    if math.isnan(value):
        return MISSING
    if math.isinf(value):
        return ("" if value > 0 else symbols["minus"]) + "∞"
    text = fixed_text(abs(value), digits)
    integer_part, _, fraction = text.partition(".")
    body = group_thousands(integer_part, symbols["thousands"]) + (symbols["decimal"] + fraction if fraction else "")
    is_negative = value < 0 and any(character not in "0." for character in text)
    return (symbols["minus"] if is_negative else "") + body


def quantile_places(value: float, digits: int, whole: bool) -> int:
    """Decimals for a quantile: of small whole numbers (below 10, where whole numbers get no decimals by
    study.digit_steps), one that falls between two of them keeps one more: a median score of 2.5, not 3. Larger
    ones round as usual (an age quartile of 55.5 reads 56)."""
    snapped = round(float(value), 10)
    small = abs(snapped) < load_tokens()["study"]["digit_steps"][0]["min"]
    return digits + 1 if whole and small and snapped != round(snapped) else digits


def format_percent(share: float, digits: int = 1, locale: str | None = None) -> str:
    """Format a share (0.614) as a percentage ('61.4%' in en, '61,4 %' in de); a missing share reads as a dash."""
    symbols = locale_symbols(locale)
    if math.isnan(share):
        return MISSING
    return format_number(share * 100, digits, locale) + symbols["percent_space"] + "%"


def format_interval(estimate: float, low: float, high: float, digits: int = 2, locale: str | None = None) -> str:
    """Format an estimate with its interval: '0.58 [0.41; 0.82]'."""
    parts = [format_number(value, digits, locale) for value in (estimate, low, high)]
    return f"{parts[0]} [{parts[1]}; {parts[2]}]"


def format_p(value: float, locale: str | None = None) -> str:
    """A p-value for reading: 'p < 0.001', three decimals below 0.1, two above; NaN (a test that all-equal values
    leave undefined) reads 'p not defined'."""
    if math.isnan(value):
        return "p not defined"
    if value < 0.001:
        return f"p < {format_number(0.001, 3, locale)}"
    return f"p = {format_number(value, 3 if value < 0.1 else 2, locale)}"


def is_whole(values) -> bool:
    import numpy as np
    array = np.asarray(values, dtype=float)
    return bool(len(array)) and bool(np.all(array == np.round(array)))


def places_for(size: float) -> int:
    """Decimals that give `size` (above zero) at least one unit in the last place."""
    return max(0, math.ceil(-math.log10(size) - ROUNDING_TOLERANCE))


def significant_places(value: float, least: int = 2) -> int:
    """Decimals that show `value` with two significant digits, at least `least` (a slope of 0.000407 is 0.00041,
    not 0.00), up to study.max_digits."""
    if not value or not math.isfinite(value):
        return least
    return min(max(least, places_for(abs(value)) + 1), load_tokens()["study"]["max_digits"])


def auto_digits(values) -> int:
    """Decimals for values and their quantiles: none for whole numbers (counts, scores), otherwise by the median
    magnitude: none from 10, one from 1, two below (tokens study.digit_steps). More where the interquartile range
    (or, without one, the magnitude) would round away, so 1000.2 ± 0.1 and 0.0004 keep their digits, up to
    study.max_digits. Means take one more for whole data."""
    import numpy as np
    array = np.asarray(values, dtype=float)
    array = array[np.isfinite(array)]
    if is_whole(array) or not len(array):
        return 0
    magnitude = float(np.median(np.abs(array)))
    rules = load_tokens()["study"]
    steps = rules["digit_steps"]
    digits = next((step["digits"] for step in steps if magnitude >= step["min"]), steps[-1]["digits"])
    low, high = np.quantile(array, [0.25, 0.75])
    spread = float(high - low) or float(array.max() - array.min())
    for size in (spread, magnitude):
        if size > 0:
            digits = max(digits, places_for(size))
    return min(digits, rules["max_digits"])
