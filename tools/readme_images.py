"""Images for the repository README: a hero figure, one thumbnail per chart and a Python-next-to-R sheet, from the
gallery output (run the gallery first: tools/parity.py runs it). Run from python/: uv run python
../tools/readme_images.py."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

import hairline as hl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from overview import CHARTS, tile  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "gallery" / "out"
IMAGES = REPO / "docs" / "images"
HERO, HERO_WIDTH, THUMB_WIDTH = "occupancy_rows", 1600, 760
LEFT_OUT = {"colour_sets", "theme_scatter"}
PARITY = [("km_trial", "Kaplan–Meier"), ("forest_meta", "Forest plot")]
PARITY_WIDTH_MM, PARITY_HEIGHT_MM, PARITY_DPI = 260, 168, 160
BRAND_HEIGHT_MM = 100


def downscaled(source: Path, target: Path, width: int) -> None:
    with Image.open(source) as image:
        height = round(image.height * width / image.width)
        image.convert("RGB").resize((width, height), Image.LANCZOS).save(target, optimize=True)


def parity_sheet(target: Path) -> None:
    tiles = [(OUT / language / f"{name}.png", f"{title} · {label}") for name, title in PARITY
             for language, label in (("python", "Python"), ("r", "R"))]
    figure = hl.figure("The same figure in Python and R", subtitle="One gallery script per language, side by side",
                       width_mm=PARITY_WIDTH_MM, height_mm=PARITY_HEIGHT_MM, panels=len(tiles), layout="compose",
                       columns=2)
    for index, (path, label) in enumerate(tiles):
        tile(figure, index, path, label)
    hl.save(figure, target, formats=("png",), dpi=PARITY_DPI)


def brand_sheet(target: Path) -> None:
    """The same scatter plot from the gallery, without a brand and with the example brand file."""
    tiles = [(OUT / "python" / "theme_scatter.png", "Without a brand"),
             (OUT / "python" / "brand_example.png", "With brands/example/_brand.yml")]
    figure = hl.figure("One brand file, every figure",
                       subtitle="Colours, fonts, sizes and number format from _brand.yml",
                       width_mm=PARITY_WIDTH_MM, height_mm=BRAND_HEIGHT_MM, panels=2, layout="compose", columns=2)
    for index, (path, label) in enumerate(tiles):
        tile(figure, index, path, label)
    hl.save(figure, target, formats=("png",), dpi=PARITY_DPI)


def main() -> int:
    missing = [name for name, _ in CHARTS if not (OUT / "python" / f"{name}.png").exists()]
    if missing:
        sys.stderr.write(f"hairline readme images: run the gallery first; missing {', '.join(missing)}\n")
        return 1
    hl.use(brand=False)
    (IMAGES / "gallery").mkdir(parents=True, exist_ok=True)
    downscaled(OUT / "python" / f"{HERO}.png", IMAGES / "hero.png", HERO_WIDTH)
    for name, _ in CHARTS:
        if name not in LEFT_OUT:
            downscaled(OUT / "python" / f"{name}.png", IMAGES / "gallery" / f"{name}.png", THUMB_WIDTH)
    parity_sheet(IMAGES / "parity")
    brand_sheet(IMAGES / "brand")
    return 0


if __name__ == "__main__":
    sys.exit(main())
