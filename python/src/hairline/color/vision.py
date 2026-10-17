"""Colour-vision simulation (Machado, Oliveira & Fernandes 2009, severity 1.0), distance and contrast."""

from __future__ import annotations

import math
from typing import Literal

from hairline.color.space import hex_to_linear, linear_to_hex, linear_to_oklab

Deficiency = Literal["protan", "deutan"]
MACHADO = {
    "protan": ((0.152286, 1.052583, -0.204868),
               (0.114503, 0.786281, 0.099216),
               (-0.003882, -0.048116, 1.051998)),
    "deutan": ((0.367322, 0.860646, -0.227968),
               (0.280085, 0.672501, 0.047413),
               (-0.011820, 0.042940, 0.968881)),
}


def simulate_linear(color: str, kind: Deficiency) -> tuple[float, float, float]:
    if kind not in MACHADO:
        raise ValueError(f"hairline: unknown colour-vision deficiency {kind!r}; use 'protan' or 'deutan'")
    linear = hex_to_linear(color)
    return tuple(min(1.0, max(0.0, sum(weight * value for weight, value in zip(row, linear, strict=True))))
                 for row in MACHADO[kind])


def simulate(color: str, kind: Deficiency) -> str:
    """Return how `color` appears with the given deficiency, as hex."""
    return linear_to_hex(*simulate_linear(color, kind))


def delta_e(first: str, second: str, kind: Deficiency | None = None) -> float:
    """Euclidean OKLab distance x 100, optionally after simulating a deficiency."""
    if kind is None:
        a, b = linear_to_oklab(*hex_to_linear(first)), linear_to_oklab(*hex_to_linear(second))
    else:
        a, b = linear_to_oklab(*simulate_linear(first, kind)), linear_to_oklab(*simulate_linear(second, kind))
    return 100 * math.dist(a, b)


def relative_luminance(color: str) -> float:
    red, green, blue = hex_to_linear(color)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(first: str, second: str) -> float:
    """WCAG contrast ratio between two colours (order does not matter)."""
    high, low = sorted((relative_luminance(first), relative_luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)
