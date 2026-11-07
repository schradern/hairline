"""Images for the repository README: a hero figure, one thumbnail per chart, a Python-next-to-R sheet, one data set
in four charts and two charts with and without a brand, from the gallery output (run the gallery first:
tools/parity.py runs it). Run from python/: uv run python ../tools/readme_images.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from PIL import Image

import hairline as hl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from overview import CHARTS, tile  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "gallery" / "out"
IMAGES = REPO / "docs" / "images"
HERO, HERO_WIDTH, THUMB_WIDTH = "occupancy_rows", 1600, 1100
LEFT_OUT = {"colour_sets", "theme_scatter"}
PARITY = [("km_trial", "Kaplan–Meier"), ("forest_meta", "Forest plot")]
PARITY_WIDTH_MM, PARITY_HEIGHT_MM, PARITY_DPI = 260, 168, 160
CONSISTENT = [("bars_percent", "Stacked bars"), ("donut_discharge", "Donut"), ("partition_discharge", "Partition bars"),
              ("donut_nested", "Nested donut")]
CONSISTENT_HEIGHT_MM = 190
BRAND = REPO / "brands" / "example" / "_brand.yml"
DATA = REPO / "gallery" / "data"


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


def compose(tiles: list[tuple[Path, str]], title: str, subtitle: str, height_mm: float, target: Path) -> None:
    figure = hl.figure(title, subtitle=subtitle, width_mm=PARITY_WIDTH_MM, height_mm=height_mm, panels=len(tiles),
                       layout="compose", columns=2)
    for index, (path, label) in enumerate(tiles):
        tile(figure, index, path, label)
    hl.save(figure, target, formats=("png",), dpi=PARITY_DPI)


def consistency_sheet(target: Path) -> None:
    """One data set in four chart types: the same frame slots and the same colour for each destination."""
    compose([(OUT / "python" / f"{name}.png", label) for name, label in CONSISTENT], "One design, every chart",
            "Where patients go after the ICU, four ways: each destination keeps its colour, each figure its frame",
            CONSISTENT_HEIGHT_MM, target)


def branded_charts(folder: Path) -> list[Path]:
    """Two gallery charts drawn again with the example brand file, as the gallery scripts draw them."""
    hl.use(brand=BRAND)
    try:
        bars = hl.bars(pd.read_csv(DATA / "admissions.csv"), "diagnosis", by="sex",
                       subtitle="Admissions to all ICUs, 2025", caption="Synthetic data.", size="double")
        survival = hl.kaplan_meier(pd.read_csv(DATA / "trial.csv"), "months", "died", by="arm",
                                   order=["Standard care", "Early mobilisation"], title="Survival after ICU discharge",
                                   subtitle="Kaplan–Meier estimate with 95% bands", caption="Synthetic data.",
                                   x_title="Months since discharge", endpoint="Overall survival", size="double")
        paths = [folder / "bars_admissions", folder / "km_trial"]
        for figure, path in zip((bars, survival), paths, strict=True):
            hl.save(figure, path, formats=("png",))
    finally:
        hl.use(brand=False)
    return [path.with_suffix(".png") for path in paths]


def brand_sheet(target: Path) -> None:
    """Two charts from the gallery, without a brand and with the example brand file."""
    folder = OUT / "readme"
    folder.mkdir(parents=True, exist_ok=True)
    bars, survival = branded_charts(folder)
    tiles = [(OUT / "python" / "bars_admissions.png", "Bar chart · no brand"),
             (bars, "Bar chart · brands/example/_brand.yml"),
             (OUT / "python" / "km_trial.png", "Kaplan–Meier · no brand"),
             (survival, "Kaplan–Meier · brands/example/_brand.yml")]
    compose(tiles, "One brand file, every chart", "Colours, sizes and number format from _brand.yml; the layout "
            "rules stay hairline's", PARITY_HEIGHT_MM, target)


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
    consistency_sheet(IMAGES / "consistency")
    brand_sheet(IMAGES / "brand")
    return 0


if __name__ == "__main__":
    sys.exit(main())
