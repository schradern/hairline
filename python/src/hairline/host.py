"""Host integration: an editor that runs code inside documents hands hairline
the document's context through a JSON file named by HAIRLINE_HOST_CONTEXT; hairline answers with figure files and
a manifest. Nothing here is specific to one host."""

from __future__ import annotations

import json
import math
import numbers
import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path

from hairline.tokens import load_tokens

ENVIRONMENT = "HAIRLINE_HOST_CONTEXT"
VERSION = 1
MANIFEST = "hairline-figures.json"
OUTPUTS = ("screen", "pdf", "html", "docx")
FORMATS = {"screen": ("png",), "pdf": ("pdf", "png"), "docx": ("pdf", "png"), "html": ("svg", "png")}

_state: dict[str, object] = {"path": None, "context": None, "warned": set(), "handing_off": False}


@dataclass(frozen=True)
class HostContext:
    host: str
    output: str = "screen"
    brand: str | list[str] | None = None
    interactive: bool = False
    width_mm: float | None = None
    locale: str | None = None
    base_size: float | None = None
    figure_dir: Path | None = None
    design: dict = field(default_factory=dict)
    dpi: int | None = None


def warn_once(path: str, problem: str) -> None:
    if (path, problem) not in _state["warned"]:
        _state["warned"].add((path, problem))
        warnings.warn(f"hairline: host context {path}: {problem}; continuing without it", UserWarning, stacklevel=3)


def positive_number(path: str, value: object, key: str) -> float | None:
    """A size or resolution from the context: a number above zero, else warned about and left out."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, numbers.Real) or not math.isfinite(value) or value <= 0:
        warn_once(path, f"{key} {value!r} must be a number above zero")
        return None
    return value


def host_locale(path: str, value: object) -> str | None:
    """The context's locale as hairline names it ("de-DE" and "de_AT" are "de"); one hairline lacks is warned about
    and left out, so figures keep the session's locale."""
    if value is None:
        return None
    locales = load_tokens()["locales"]
    if isinstance(value, str):
        language = value.replace("_", "-").split("-")[0].lower()
        if value in locales or language in locales:
            return value if value in locales else language
    warn_once(path, f"locale {value!r} is not one of {', '.join(sorted(locales))}")
    return None


def read_context(path: str) -> dict | None:
    """The file's content when it is a version-1 context with a known output, else None (warned once)."""
    try:
        content = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        warn_once(path, "the file does not exist")
        return None
    except json.JSONDecodeError as error:
        warn_once(path, f"not valid JSON ({error.msg}, line {error.lineno})")
        return None
    if not isinstance(content, dict) or content.get("version") != VERSION:
        warn_once(path, f"version {content.get('version') if isinstance(content, dict) else None!r} is not {VERSION}")
        return None
    if content.get("output", "screen") not in OUTPUTS:
        warn_once(path, f"output {content['output']!r} must be one of {', '.join(OUTPUTS)}")
        return None
    return content


def parse_context(path: str) -> HostContext | None:
    """A context from the file; values of the wrong kind are warned about and left out, the rest applies."""
    content = read_context(path)
    if content is None:
        return None
    output, folder, design = content.get("output", "screen"), content.get("figure_dir"), content.get("design")
    if folder is not None and not isinstance(folder, str):
        folder = warn_once(path, f"figure_dir {folder!r} must be a folder path")
    if design is not None and not isinstance(design, dict):
        design = warn_once(path, f"design {design!r} must be a mapping")
    width, base, dpi = (positive_number(path, content.get(key), key) for key in ("width_mm", "base_size", "dpi"))
    return HostContext(host=str(content.get("host", "host")), output=output, brand=content.get("brand"),
                       interactive=content.get("interactive") is True and output == "html", width_mm=width,
                       locale=host_locale(path, content.get("locale")), base_size=base,
                       figure_dir=Path(folder) if folder else None, design=dict(design or {}), dpi=dpi)


def host_context() -> HostContext | None:
    """The current context, re-read when the variable points to another file. A new context re-applies the
    session's style (keeping the arguments passed to `use()`), so a host that switches output, font or brand
    between runs of one long-lived session gets figures in the new style."""
    path = os.environ.get(ENVIRONMENT)
    if not path:
        return None
    if path != _state["path"]:
        _state["path"], _state["context"] = path, parse_context(path)
        if _state["context"] is not None:
            from hairline.settings import reapply
            try:
                reapply()
            except ValueError as error:
                warn_once(path, f"its style could not be applied ({error})")
    return _state["context"]


def read_manifest(path: Path) -> list:
    """The figures already listed; a manifest that is not a list of figures is replaced, with a warning, so one
    damaged file does not stop every later figure."""
    if not path.is_file():
        return []
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        entries = None
    if isinstance(entries, list):
        return entries
    warnings.warn(f"hairline: host manifest {path} is not a list of figures; starting a new one", UserWarning,
                  stacklevel=3)
    return []


def hand_off(figure) -> None:
    """Write a displayed figure to the host's folder in the formats its output needs, and list it in the
    manifest (id, files, size, alt text). Runs once per figure and figure folder, after the host's own save: a
    host that empties the folder between runs (the manifest is gone) gets a figure shown again handed off again."""
    context = host_context()
    if context is None or context.figure_dir is None or _state["handing_off"]:
        return
    if getattr(figure, "handed_off", False) and (context.figure_dir / MANIFEST).is_file():
        return
    from hairline.export import figure_alt, save
    _state["handing_off"] = True
    try:
        context.figure_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = context.figure_dir / MANIFEST
        entries = read_manifest(manifest_path)
        figure_id = f"figure-{len(entries) + 1}"
        dpi = context.dpi if context.output == "screen" and context.dpi else None
        formats = FORMATS[context.output] + (("html",) if context.interactive else ())
        paths = save(figure, context.figure_dir / figure_id, formats=formats, dpi=dpi)
        width, height = (value * 25.4 for value in figure.figure.get_size_inches())
        entries.append({"id": figure_id, "files": {path.suffix[1:]: str(path) for path in paths},
                        "width_mm": round(width, 2), "height_mm": round(height, 2), "alt": figure_alt(figure)})
        manifest_path.write_text(json.dumps(entries, indent=1), encoding="utf-8")
        figure.handed_off = True
    finally:
        _state["handing_off"] = False
