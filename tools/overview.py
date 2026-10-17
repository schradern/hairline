"""Gallery overview sheets: every chart type on one page per language, and Python next to R for each chart.

Run after the gallery scripts (tools/parity.py runs them); writes gallery/out/overview_<language>.{png,pdf} and
gallery/out/overview_parity.png.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import matplotlib.image as mpimg

import hairline as hl

REPO = Path(__file__).resolve().parents[1]
CHARTS = [("donut_discharge", "Donut"), ("donut_nested", "Nested donut"), ("partition_discharge", "Partition bars"),
          ("km_trial", "Kaplan–Meier"), ("forest_meta", "Forest plot"), ("raincloud_stay", "Raincloud"),
          ("sankey_budget", "Sankey"), ("occupancy_rows", "Time series, two levels of detail"),
          ("grid_panels", "Small multiples"), ("theme_scatter", "Scatter with the theme"),
          ("brand_example", "Brand file")]
LANGUAGES = {"python": "Python", "r": "R"}
SHEET_WIDTH_MM = 420
OVERVIEW_DPI = 200


def missing_images(gallery: Path) -> list[str]:
    return [f"{language}/{name}.png" for language in LANGUAGES for name, _ in CHARTS
            if not (gallery / "out" / language / f"{name}.png").exists()]


def tile(figure: hl.HairlineFigure, index: int, path: Path, title: str) -> None:
    image = mpimg.imread(path)
    figure.axes[index].imshow(image, interpolation="lanczos")
    figure.axes[index].set_aspect("auto")
    figure.bare(index, aspect=image.shape[0] / image.shape[1])
    figure.panel_header(index, title)


def sheet(tiles: list[tuple[Path, str]], columns: int, title: str, subtitle: str, output: Path) -> None:
    rows = math.ceil(len(tiles) / columns)
    tile_width = (SHEET_WIDTH_MM - 30) / columns
    figure = hl.figure(title, subtitle=subtitle, caption="Synthetic data throughout; each tile is a gallery PNG.",
                       width_mm=SHEET_WIDTH_MM, height_mm=rows * (tile_width * 0.74 + 12) + 45, panels=len(tiles),
                       layout="compose", columns=columns)
    for index, (path, label) in enumerate(tiles):
        tile(figure, index, path, label)
    hl.save(figure, output, formats=("png", "pdf"), dpi=OVERVIEW_DPI)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gallery", type=Path, default=REPO / "gallery", help="gallery folder with out/<language>")
    gallery = parser.parse_args().gallery
    missing = missing_images(gallery)
    if missing:
        sys.stderr.write("".join(f"hairline overview: {gallery / 'out' / path} is missing; run the gallery first\n"
                                 for path in missing))
        return 1
    hl.use(brand=False)
    out = gallery / "out"
    for language, label in LANGUAGES.items():
        sheet([(out / language / f"{name}.png", title) for name, title in CHARTS], 3, "hairline chart gallery",
              f"Every chart type, drawn by the {label} package", out / f"overview_{language}")
    pairs = [(out / language / f"{name}.png", f"{title} · {label}") for name, title in CHARTS
             for language, label in LANGUAGES.items()]
    sheet(pairs, 2, "hairline in Python and R", "The same gallery script in both languages, side by side",
          out / "overview_parity")
    return 0


if __name__ == "__main__":
    sys.exit(main())
