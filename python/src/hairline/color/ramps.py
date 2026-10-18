"""The ramp rule: sequential ramps from one hue, diverging ramps from two, in OKLCH. The token
ramps and a brand's ramps both come from here; mirrored in R's sequential_ramp() and diverging_ramp()."""

from __future__ import annotations

import math

from hairline.color.space import oklch_to_hex
from hairline.tokens import load_tokens


def sequential_ramp(hue: float | None, definition: dict | None = None) -> list[str]:
    """Light to dark in one hue (`None`: greys); chroma peaks in the middle steps."""
    definition = definition or load_tokens()["ramp_definitions"]
    steps = definition["steps"]
    light, dark = definition["lightness"]
    colors = []
    for index in range(steps):
        lightness = light + (dark - light) * index / (steps - 1)
        envelope = 0.35 + 0.65 * math.sin(math.pi * (0.15 + 0.7 * index / (steps - 1)))
        chroma = 0.0 if hue is None else definition["chroma_peak"] * envelope
        colors.append(oklch_to_hex(lightness, chroma, hue or 0.0))
    return colors


def diverging_ramp(low_hue: float, high_hue: float, definition: dict | None = None) -> list[str]:
    """The low arm dark to light, the neutral midpoint, the high arm light to dark."""
    definition = definition or load_tokens()["ramp_definitions"]
    low, high = sequential_ramp(low_hue, definition), sequential_ramp(high_hue, definition)
    return list(reversed(low[1:])) + [definition["midpoint"]] + high[1:]
