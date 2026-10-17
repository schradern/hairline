"""Panels without axes (donut, Sankey, partition bars) and fixed-aspect plot areas inside a panel box."""

from __future__ import annotations

from hairline.layout.geometry import Box


def fitted_box(box: Box, aspect: float | None) -> Box:
    """The panel box, or the largest box of height/width `aspect` inside it, centred horizontally, top-aligned."""
    if aspect is None:
        return box
    width = min(box.width, box.height / aspect)
    height = width * aspect
    return Box(box.x + (box.width - width) / 2, box.y, width, height)
