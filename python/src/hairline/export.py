"""save(): print-ready PDF, PNG, SVG and TIFF in one call, named by the figure's title, without timestamps or
producer banners."""

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


def figure_alt(owner: HairlineFigure) -> str:
    """The figure's alt text: title and subtitle, leaving out a missing or empty one."""
    return ". ".join(part for part in (owner.title, owner.subtitle) if part)


def figure_name(fig: Figure) -> tuple[str, str] | None:
    """Title and description (the alt text that the HTML figure and the host manifest give too)."""
    owner = getattr(fig, "hairline_figure", None)
    if owner is None or not owner.title:
        return None
    return owner.title, figure_alt(owner)


def named_metadata(name: str, naming: tuple[str, str] | None) -> dict | None:
    """The format's metadata with the figure's name: PDF Title and Subject, PNG Title and Description."""
    fields = {"pdf": ("Title", "Subject"), "png": ("Title", "Description")}.get(name)
    if naming is None or fields is None:
        return METADATA.get(name)
    return {**METADATA[name], **dict(zip(fields, naming, strict=True))}


def name_svg(path: Path, naming: tuple[str, str]) -> None:
    """<title> and <desc> as the root element's first children, which viewers and screen readers read."""
    text = path.read_text(encoding="utf-8")
    title, description = (part.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") for part in naming)
    end = text.index(">", text.index("<svg")) + 1
    path.write_text(f"{text[:end]}<title>{title}</title><desc>{description}</desc>{text[end:]}", encoding="utf-8")


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
    path.write_text(page(owner.title, figure_html(buffer.getvalue(), targets, owner.settings.font, figure_alt(owner)),
                         targets["style"]["surface"]), encoding="utf-8")


def write_one(fig: Figure, path: Path, name: str, dpi: int, options: dict) -> None:
    if name == "html":
        write_html(fig, path, options)
    elif name == "tiff":
        write_tiff(fig, path, dpi, options)
    else:
        naming = figure_name(fig)
        with path.open("wb") as handle:
            fig.savefig(handle, format=name, dpi=dpi, metadata=named_metadata(name, naming), **options)
        if name == "svg" and naming:
            name_svg(path, naming)


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
            raise RuntimeError(f"hairline: writing {path} failed: {type(error).__name__}: {error}") from error
        written.append(path)
    return written


def strip_known_extension(base: Path) -> Path:
    """'fig.pdf' and 'fig' both mean the base name 'fig'."""
    if base.suffix.lower().lstrip(".") in load_tokens()["export"]["valid_formats"]:
        return base.with_suffix("")
    return base
