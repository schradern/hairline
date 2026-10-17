"""Tints of a parent colour for its children (nested donut rings, partition bars)."""

from __future__ import annotations

from hairline.color.space import hex_to_oklch, oklch_to_hex
from hairline.tokens import load_tokens


def tints(color: str, count: int) -> list[str]:
    """`count` shades of `color` with its hue and chroma, stepped lighter, or darker when lighter would pass the cap."""
    rules = load_tokens()["tints"]
    lightness, chroma, hue = hex_to_oklch(color)
    direction = 1 if lightness + rules["step"] * count <= rules["cap"] else -1
    room = rules["cap"] - lightness if direction > 0 else lightness - rules["floor"]
    step = min(rules["step"], max(room, 0.0) / max(count, 1))
    return [oklch_to_hex(lightness + direction * step * (index + 1), chroma, hue) for index in range(count)]
