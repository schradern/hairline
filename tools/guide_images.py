"""Build the images of docs/guide/colours.md with the Python package (run from python/: uv run python
../tools/guide_images.py)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

import hairline as hl

IMAGES = Path(__file__).resolve().parents[1] / "docs" / "guide" / "images"
DPI = 150


def colour_by_count() -> hl.HairlineFigure:
    """Two, three and four groups take the first two, three and four colours of the palette."""
    figure = hl.figure("Colour by count", subtitle="A group keeps its colour when more groups are shown",
                       size="onehalf", panels=3, layout="compose", columns=3)
    for index, count in enumerate((2, 3, 4)):
        names = [f"Unit {letter}" for letter in "ABCD"[:count]]
        figure.axes[index].bar(range(count), [4, 3, 5, 2][:count], color=hl.palette(n=count))
        figure.categories(index, [name[-1] for name in names])
        figure.panel_header(index, f"{count} groups")
    return figure


def highlight() -> hl.HairlineFigure:
    days = np.arange(60)
    waves = [level + 0.06 * np.sin(days / 6 + shift) for level, shift in ((0.7, 0), (0.85, 1), (0.6, 2))]
    occupancy = pd.DataFrame({"date": list(pd.date_range("2025-01-01", periods=60)) * 3,
                              "unit": np.repeat(["Unit A", "Unit B", "Unit C"], 60), "share": np.concatenate(waves)})
    return hl.timeseries(occupancy, "date", "share", by="unit", percent=True, highlight=["Unit B"])


def main() -> int:
    hl.use(brand=False)
    IMAGES.mkdir(parents=True, exist_ok=True)
    figures = {"colour-sets": hl.swatches(), "colour-by-count": colour_by_count(), "highlight": highlight()}
    for name, figure in figures.items():
        hl.save(figure, IMAGES / name, formats=["png"], dpi=DPI)
    return 0


if __name__ == "__main__":
    sys.exit(main())
