"""Named palettes, purpose sets and ramps from the shared tokens."""

from __future__ import annotations

from collections.abc import Sequence

from hairline.color.check import check_palette
from hairline.color.space import hex_to_oklab, linear_to_hex, oklab_to_linear, parse_hex
from hairline.tokens import load_tokens


def resolve_colors(name: str | Sequence[str] | None) -> tuple[str, list[str]]:
    tokens = load_tokens()
    if name is None:
        from hairline.settings import current_settings
        active = current_settings()
        return active.palette_label, list(active.palette)
    if isinstance(name, str):
        if name not in tokens["palettes"]:
            known = ", ".join(tokens["palettes"])
            raise ValueError(f"hairline: unknown palette {name!r}; available palettes: {known}")
        return f"palette {name!r}", list(tokens["palettes"][name])
    colors = list(name)
    for color in colors:
        parse_hex(color)
    return "custom palette", colors


def palette(name: str | Sequence[str] | None = None, n: int | None = None) -> list[str]:
    """Return palette colours in slot order; `n` takes the first n slots and never repeats colours."""
    label, colors = resolve_colors(name)
    if n is None:
        return colors
    if n > len(colors):
        raise ValueError(f"hairline: {label} has {len(colors)} slots but {n} categories were given; "
                         "fold small categories into 'Other' or split the figure into panels")
    return colors[:n]


def light_slots(colors: Sequence[str], surface: str | None = None) -> list[int]:
    """1-based slots below 3:1 contrast against the surface."""
    return check_palette(colors, surface or load_tokens()["neutral"]["surface"]).light_slots


def interpolate(colors: Sequence[str], count: int) -> list[str]:
    points = [hex_to_oklab(color) for color in colors]
    result = []
    for index in range(count):
        position = index * (len(points) - 1) / max(count - 1, 1)
        low = min(int(position), len(points) - 2)
        weight = position - low
        mixed = [a + (b - a) * weight for a, b in zip(points[low], points[low + 1], strict=True)]
        result.append(linear_to_hex(*oklab_to_linear(*mixed)))
    return result


def ramp(name: str, n: int | None = None) -> list[str]:
    """Return a sequential or diverging ramp, light to dark (diverging: low pole to high pole)."""
    ramps = load_tokens()["ramps"]
    if name not in ramps:
        raise ValueError(f"hairline: unknown ramp {name!r}; available ramps: {', '.join(ramps)}")
    colors = list(ramps[name])
    return colors if n is None or n == len(colors) else interpolate(colors, n)
