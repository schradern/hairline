"""Measure and wrap text in pt with a dedicated renderer at 100 times 72 dpi, so glyph advances are not rounded."""

from __future__ import annotations

from functools import lru_cache

from matplotlib.backends.backend_agg import RendererAgg
from matplotlib.font_manager import FontProperties

POINTS_PER_INCH = 72
MEASURE_SCALE = 100


@lru_cache(maxsize=1)
def measuring_renderer() -> RendererAgg:
    return RendererAgg(16, 16, POINTS_PER_INCH * MEASURE_SCALE)


def font(family: str, size: float, weight: int = 400) -> FontProperties:
    return FontProperties(family=family, size=size, weight=weight)


@lru_cache(maxsize=4096)
def text_width(text: str, family: str, size: float, weight: int = 400) -> float:
    """Advance width of `text` in pt."""
    if not text:
        return 0.0
    width, _, _ = measuring_renderer().get_text_width_height_descent(text, font(family, size, weight), ismath=False)
    return float(width) / MEASURE_SCALE


def wrap(text: str, family: str, size: float, weight: int, max_width: float) -> list[str]:
    """Greedy word wrap; a single word longer than the line stays on its own line."""
    lines: list[str] = []
    for paragraph in text.split("\n"):
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}" if current else word
            if current and text_width(candidate, family, size, weight) > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
    return lines
