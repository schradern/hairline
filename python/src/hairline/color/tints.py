"""Tints of a parent colour for its children (nested donut rings, partition bars)."""

from __future__ import annotations

from hairline.color.space import hex_to_oklch, oklch_to_hex
from hairline.tokens import load_tokens


def tints(color: str, count: int) -> list[str]:
    """`count` lighter shades of `color` with its hue and chroma, evenly stepped up to the lightness cap."""
    rules = load_tokens()["tints"]
    lightness, chroma, hue = hex_to_oklch(color)
    step = min(rules["step"], max(rules["cap"] - lightness, 0.0) / max(count, 1))
    return [oklch_to_hex(lightness + step * (index + 1), chroma, hue) for index in range(count)]
