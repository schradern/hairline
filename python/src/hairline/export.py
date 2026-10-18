"""save(): print-ready PDF, PNG, SVG and TIFF in one call, without timestamps or producer banners."""

from __future__ import annotations

import io
import os
from collections.abc import Sequence
from pathlib import Path

from matplotlib.figure import Figure
from PIL import Image

from hairline.figure import HairlineFigure
from hairline.tokens import load_tokens

METADATA = {
    "pdf": {"Creator": None, "Producer": None, "CreationDate": None},
    "svg": {"Date": None, "Creator": None},
    "png": {"Software": None},
}


def validated_formats(formats: Sequence[str]) -> list[str]:
    valid = load_tokens()["export"]["valid_formats"]
    requested = [formats] if isinstance(formats, str) else list(formats)
    for name in requested:
        if name not in valid:
            raise ValueError(f"hairline: unknown format {name!r}; use one of {', '.join(valid)}")
    if not requested:
        raise ValueError(f"hairline: no output format given; use one or more of {', '.join(valid)}")
    return requested


def write_tiff(fig: Figure, path: Path, dpi: int, options: dict) -> None:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=dpi, metadata=METADATA["png"], **options)
    buffer.seek(0)
    with Image.open(buffer) as image:
        image.save(path, format="TIFF", compression="tiff_lzw", dpi=(dpi, dpi))


def write_html(fig: Figure, path: Path, options: dict) -> None:
    """The static SVG with tooltips and series highlighting."""
    from hairline.interactive import figure_html, figure_targets, page
    owner = getattr(fig, "hairline_figure", None)
    if owner is None:
        raise ValueError("hairline: html export needs a figure made with hairline.figure() or a chart function")
    buffer = io.StringIO()
    fig.savefig(buffer, format="svg", metadata=METADATA["svg"], **options)
    targets = figure_targets(owner)
    path.write_text(page(owner.title, figure_html(buffer.getvalue(), targets, owner.settings.font)),
                    encoding="utf-8")


def write_one(fig: Figure, path: Path, name: str, dpi: int, options: dict) -> None:
    if name == "html":
        write_html(fig, path, options)
    elif name == "tiff":
        write_tiff(fig, path, dpi, options)
    else:
        with path.open("wb") as handle:
            fig.savefig(handle, format=name, dpi=dpi, metadata=METADATA.get(name), **options)


def save(figure: HairlineFigure | Figure, name: str | os.PathLike, formats: Sequence[str] = ("pdf", "png"),
         dpi: int | None = None, background: str | None = None) -> list[Path]:
    """Write `name.<format>` for each format; returns the paths. Parent folders are created."""
    requested = validated_formats(formats)
    fig = figure.figure if isinstance(figure, HairlineFigure) else figure
    dpi = dpi or load_tokens()["export"]["dpi"]
    options = {"transparent": True} if background == "transparent" else {}
    base = strip_known_extension(Path(name))
    base.parent.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for format_name in requested:
        path = base.with_name(f"{base.name}.{format_name}")
        partial = path.with_name(f".{path.name}.partial")
        try:
            write_one(fig, partial, format_name, dpi, options)
            os.replace(partial, path)
        except Exception as error:
            for leftover in [partial, *written]:
                leftover.unlink(missing_ok=True)
            raise RuntimeError(f"hairline: writing {path} failed: {error}") from error
        written.append(path)
    return written


def strip_known_extension(base: Path) -> Path:
    """'fig.pdf' and 'fig' both mean the base name 'fig'."""
    if base.suffix.lower().lstrip(".") in load_tokens()["export"]["valid_formats"]:
        return base.with_suffix("")
    return base
