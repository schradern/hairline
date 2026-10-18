"""swatches(): the colour sets drawn as rows of squares, to choose a palette or a ramp by eye."""

from __future__ import annotations

from collections.abc import Sequence

from hairline.charts.swatches_geometry import swatches_drawing
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.palettes import swatch_rows


def swatches(names: str | Sequence[str] | None = None, *, title: str | None = None, subtitle: str | None = None,
             caption: str | None = None, size: str = "onehalf") -> HairlineFigure:
    """Palettes, purpose sets and ramps as rows of squares under their headings, each with its use; `names`
    picks some of them (as `palettes()` lists them), in catalogue order. Hover a square in HTML for its hex."""
    rows = swatch_rows([names] if isinstance(names, str) else names)
    result = figure(title or "Colour sets", subtitle=subtitle, caption=caption, size=size)
    result.draw(0, lambda box, measure, style: swatches_drawing({"rows": rows}, box, measure, style))
    return fit_height(result)
