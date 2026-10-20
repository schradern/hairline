"""Locale-aware number formatting shared with the R package."""

from __future__ import annotations

import math

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
FLOAT_NOISE = 1e-15


def fixed_text(magnitude: float, digits: int) -> str:
    """`magnitude` (zero or more) with `digits` decimals, halves rounded up. Float noise does not decide
    (8.649999999999999 is 8.65): a billionth of the last digit, plus the few units in the last place that float
    arithmetic leaves on large numbers. Neither ever adds a displayed unit, so every platform prints the same
    digits and exact values stay exact (1,000,000,000 is not 1,000,000,001)."""
    scaled = magnitude * 10**digits
    units = str(math.floor(scaled + 0.5 + ROUNDING_TOLERANCE + FLOAT_NOISE * scaled))
    if digits == 0:
        return units
    units = units.rjust(digits + 1, "0")
    return f"{units[:-digits]}.{units[-digits:]}"


def format_number(value: float, digits: int = 1, locale: str | None = None) -> str:
    """Format with fixed decimals (halves up), locale separators and a true minus sign (U+2212)."""
    symbols = locale_symbols(locale)
    text = fixed_text(abs(value), digits)
    integer_part, _, fraction = text.partition(".")
    body = group_thousands(integer_part, symbols["thousands"]) + (symbols["decimal"] + fraction if fraction else "")
    is_negative = value < 0 and any(character not in "0." for character in text)
    return (symbols["minus"] if is_negative else "") + body


def format_percent(share: float, digits: int = 1, locale: str | None = None) -> str:
    """Format a share (0.614) as a percentage ('61.4%' in en, '61,4 %' in de)."""
    symbols = locale_symbols(locale)
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


def auto_digits(values) -> int:
    """Decimals for values and their quantiles: none for whole numbers (counts, scores), otherwise by the median
    magnitude: none from 10, one from 1, two below (tokens study.digit_steps). Means take one more for whole data."""
    import numpy as np
    if is_whole(values):
        return 0
    magnitude = float(np.median(np.abs(np.asarray(values, dtype=float)))) if len(values) else 0.0
    steps = load_tokens()["study"]["digit_steps"]
    return next((step["digits"] for step in steps if magnitude >= step["min"]), steps[-1]["digits"])
