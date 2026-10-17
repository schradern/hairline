"""Step brand colours into the readable band while keeping their hues."""

from __future__ import annotations

import warnings
from collections.abc import Sequence

from hairline.color.check import check_palette, pair_indices
from hairline.color.space import hex_to_oklch, oklch_to_hex
from hairline.color.vision import delta_e
from hairline.tokens import load_tokens


def snap_into_band(color: str, limits: dict) -> list[float]:
    lightness, chroma, hue = hex_to_oklch(color)
    low, high = limits["adapt_lightness"]
    return [min(high, max(low, lightness)), max(chroma, limits["adapt_chroma"]), hue]


def weakest_pair(colors: Sequence[str]) -> tuple[int, int]:
    def separation(pair: tuple[int, int]) -> tuple[float, float]:
        a, b = colors[pair[0]], colors[pair[1]]
        return min(delta_e(a, b, "protan"), delta_e(a, b, "deutan")), delta_e(a, b)
    candidates = pair_indices(len(colors), "adjacent") + pair_indices(min(3, len(colors)), "all")
    return min(candidates, key=separation)


def nudge(slots: list[list[float]], pair: tuple[int, int], limits: dict) -> None:
    lighter, darker = sorted(pair, key=lambda index: slots[index][0], reverse=True)
    step, (_, high) = limits["adapt_step"], limits["adapt_lightness"]
    if slots[lighter][0] + step <= high:
        slots[lighter][0] += step
    else:
        slots[darker][0] -= step


def adapt_readable(colors: Sequence[str]) -> list[str]:
    """Return colours that pass the palette checks, keeping each hue."""
    if check_palette(colors).passed:
        return list(colors)
    limits = load_tokens()["checks"]
    slots = [snap_into_band(color, limits) for color in colors]
    for _ in range(limits["adapt_iterations"]):
        adapted = [oklch_to_hex(*slot) for slot in slots]
        report = check_palette(adapted)
        if report.passed:
            return adapted
        nudge(slots, weakest_pair(adapted), limits)
    adapted = [oklch_to_hex(*slot) for slot in slots]
    remaining = check_palette(adapted).failures
    if remaining:
        warnings.warn(f"hairline: colours could not be made fully readable: {'; '.join(remaining)}", stacklevel=2)
    return adapted
