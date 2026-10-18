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


def weakest_pair(colors: Sequence[str], pairs: str = "adjacent") -> tuple[int, int]:
    """The pair to separate next: lowest colour-vision ΔE (then normal ΔE); across all pairs, the pair furthest
    below either floor, so a normal-vision failure is fixed too."""
    limits = load_tokens()["checks"]

    def separation(pair: tuple[int, int]) -> tuple[float, float]:
        a, b = colors[pair[0]], colors[pair[1]]
        vision, normal = min(delta_e(a, b, "protan"), delta_e(a, b, "deutan")), delta_e(a, b)
        if pairs == "all":
            return min(vision / limits["cvd_floor"], normal / limits["normal_floor"]), vision
        return vision, normal
    candidates = pair_indices(len(colors), pairs) + pair_indices(min(3, len(colors)), "all")
    return min(candidates, key=separation)


def nudge(slots: list[list[float]], pair: tuple[int, int], limits: dict) -> None:
    lighter, darker = sorted(pair, key=lambda index: slots[index][0], reverse=True)
    step, (_, high) = limits["adapt_step"], limits["adapt_lightness"]
    if slots[lighter][0] + step <= high:
        slots[lighter][0] += step
    else:
        slots[darker][0] -= step


def adapt_readable(colors: Sequence[str], pairs: str = "adjacent") -> list[str]:
    """Return colours that pass the palette checks, keeping each hue; `pairs="all"` for
    colours that can appear in any combination (entity colours)."""
    if check_palette(colors, pairs=pairs).passed:
        return list(colors)
    limits = load_tokens()["checks"]
    slots = [snap_into_band(color, limits) for color in colors]
    for _ in range(limits["adapt_iterations"]):
        adapted = [oklch_to_hex(*slot) for slot in slots]
        report = check_palette(adapted, pairs=pairs)
        if report.passed:
            return adapted
        nudge(slots, weakest_pair(adapted, pairs), limits)
    adapted = [oklch_to_hex(*slot) for slot in slots]
    remaining = check_palette(adapted, pairs=pairs).failures
    if remaining:
        warnings.warn(f"hairline: colours could not be made fully readable: {'; '.join(remaining)}", stacklevel=2)
    return adapted
