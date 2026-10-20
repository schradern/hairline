"""save(): print-ready PDF, PNG, SVG and TIFF in one call, named by the figure's title, without timestamps or
producer banners."""

from __future__ import annotations

import io
import math
import numbers
import os
import uuid
from collections.abc import Sequence
from pathlib import Path

from matplotlib.figure import Figure
from PIL import Image, TiffImagePlugin, TiffTags

from hairline.figure import HairlineFigure
from hairline.tokens import load_tokens

METADATA = {
    "pdf": {"Creator": None, "Producer": None, "CreationDate": None},
    "svg": {"Date": None, "Creator": None},
    "png": {"Software": None},
}


def validated_formats(formats: Sequence[str] | None) -> list[str]:
    """Known formats in the order given, each once, in any case ("PNG" is png)."""
    valid = load_tokens()["export"]["valid_formats"]
    requested = [formats] if isinstance(formats, str) else list(formats or [])
    for name in requested:
        if not isinstance(name, str) or name.lower() not in valid:
            raise ValueError(f"hairline: unknown format {name!r}; use one of {', '.join(valid)}")
    if not requested:
        raise ValueError(f"hairline: no output format given; use one or more of {', '.join(valid)}")
    return list(dict.fromkeys(name.lower() for name in requested))


def save_options(dpi: float | None, background: str | None) -> tuple[float, dict]:
    """The resolution (the token default unless given, above zero) and the background: transparent, a colour, or
    the figure's own surface."""
    from matplotlib.colors import is_color_like
    dpi = load_tokens()["export"]["dpi"] if dpi is None else dpi
    if isinstance(dpi, bool) or not isinstance(dpi, numbers.Real) or not dpi > 0 or not math.isfinite(dpi):
        raise ValueError(f"hairline: save: dpi must be a number above zero; got {dpi!r}")
    if background is None:
        return dpi, {}
    if background == "transparent":
        return dpi, {"transparent": True}
    if not is_color_like(background):
        raise ValueError(f"hairline: save: background {background!r} is not a colour; use 'transparent', a colour "
                         f"such as '#ffffff', or None for the figure's own")
    return dpi, {"facecolor": background}


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


TIFF_NAME_TAGS = (269, 270)  # DocumentName (the title) and ImageDescription (title and subtitle)


def tiff_tags(naming: tuple[str, str] | None) -> TiffImagePlugin.ImageFileDirectory_v2:
    """The figure's name as UTF-8 text in ASCII-typed tags (Pillow would turn every other character into '?')."""
    tags = TiffImagePlugin.ImageFileDirectory_v2()
    for tag, text in zip(TIFF_NAME_TAGS, naming or (), strict=False):
        tags[tag] = text.encode("utf-8")
        tags.tagtype[tag] = TiffTags.ASCII
    return tags


def write_tiff(fig: Figure, path: Path, dpi: int, options: dict) -> None:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=dpi, metadata=METADATA["png"], **options)
    buffer.seek(0)
    with Image.open(buffer) as image:
        image.save(path, format="TIFF", compression="tiff_lzw", dpi=(dpi, dpi), tiffinfo=tiff_tags(figure_name(fig)))


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
    """Write `name.<format>` for each format; returns the paths. Parent folders are created. `background` is None
    for the figure's surface, "transparent", or any colour. Nothing is replaced until every format is written."""
    requested = validated_formats(formats)
    fig = figure.figure if isinstance(figure, HairlineFigure) else figure
    dpi, options = save_options(dpi, background)
    base = strip_known_extension(Path(name))
    base.parent.mkdir(parents=True, exist_ok=True)
    paths = [base.with_name(f"{base.name}.{format_name}") for format_name in requested]
    folders = [path for path in paths if path.is_dir()]
    if folders:
        raise RuntimeError(f"hairline: cannot write {folders[0]}: a folder of that name exists")
    # A link stays a link: the file it points to gets the new content.
    destinations = [path.resolve() if path.is_symlink() else path for path in paths]
    partials = [hidden_path(path, "partial") for path in destinations]
    try:
        for format_name, path, partial in zip(requested, paths, partials, strict=True):
            try:
                write_one(fig, partial, format_name, dpi, options)
            except Exception as error:
                raise RuntimeError(f"hairline: writing {path} failed: {type(error).__name__}: {error}") from error
        move_into_place(partials, destinations)
    finally:
        for partial in partials:
            partial.unlink(missing_ok=True)
    return paths


def hidden_path(path: Path, role: str) -> Path:
    """A hidden sibling for the file while it is written or backed up; short, so a long name still fits."""
    return path.with_name(f".hairline-{uuid.uuid4().hex[:12]}{path.suffix}.{role}")


def move_into_place(partials: list[Path], paths: list[Path]) -> None:
    """Every new file replaces its destination only once all are written; if one cannot be moved, the files moved
    before it get their old content back, so a failed save leaves every existing file as it was."""
    moved: list[tuple[Path, Path | None]] = []
    current = paths[0]
    try:
        for partial, path in zip(partials, paths, strict=True):
            current = path
            backup = hidden_path(path, "backup") if path.exists() else None
            if backup:
                os.replace(path, backup)
            moved.append((path, backup))
            os.replace(partial, path)
    except OSError as error:
        for path, backup in reversed(moved):
            if backup:
                os.replace(backup, path)
            else:
                path.unlink(missing_ok=True)
        raise RuntimeError(f"hairline: moving the new file into {current} failed: {error}; existing files "
                           f"keep their old content") from error
    for _, backup in moved:
        if backup:
            backup.unlink()


def strip_known_extension(base: Path) -> Path:
    """'fig.pdf' and 'fig' both mean the base name 'fig'."""
    if base.suffix.lower().lstrip(".") in load_tokens()["export"]["valid_formats"]:
        return base.with_suffix("")
    return base
