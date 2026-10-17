"""Locale-aware number formatting shared with the R package."""

from __future__ import annotations

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


def format_number(value: float, digits: int = 1, locale: str | None = None) -> str:
    """Format with fixed decimals, locale separators and a true minus sign (U+2212)."""
    symbols = locale_symbols(locale)
    text = f"{abs(value):.{digits}f}"
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
    """A p-value for reading: 'p < 0.001', three decimals below 0.1, two above."""
    if value < 0.001:
        return f"p < {format_number(0.001, 3, locale)}"
    return f"p = {format_number(value, 3 if value < 0.1 else 2, locale)}"
