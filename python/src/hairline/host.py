"""Host integration: an editor that runs code inside documents hands hairline
the document's context through a JSON file named by HAIRLINE_HOST_CONTEXT; hairline answers with figure files and
a manifest. Nothing here is specific to one host."""

from __future__ import annotations

import json
import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path

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


def parse_context(path: str) -> HostContext | None:
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
    output = content.get("output", "screen")
    if output not in OUTPUTS:
        warn_once(path, f"output {output!r} must be one of {', '.join(OUTPUTS)}")
        return None
    folder = content.get("figure_dir")
    return HostContext(host=str(content.get("host", "host")), output=output, brand=content.get("brand"),
                       interactive=bool(content.get("interactive", False)) and output == "html",
                       width_mm=content.get("width_mm"), locale=content.get("locale"),
                       base_size=content.get("base_size"), figure_dir=Path(folder) if folder else None,
                       design=dict(content.get("design") or {}), dpi=content.get("dpi"))


def host_context() -> HostContext | None:
    """The current context, re-read when the variable points to another file."""
    path = os.environ.get(ENVIRONMENT)
    if not path:
        return None
    if path != _state["path"]:
        _state["path"], _state["context"] = path, parse_context(path)
    return _state["context"]


def hand_off(figure) -> None:
    """Write a displayed figure to the host's folder in the formats its output needs, and list it in the
    manifest (id, files, size, alt text). Runs once per figure, after the host's own save."""
    context = host_context()
    if context is None or context.figure_dir is None or _state["handing_off"] or getattr(figure, "handed_off", False):
        return
    from hairline.export import save
    _state["handing_off"] = True
    try:
        manifest_path = context.figure_dir / MANIFEST
        entries = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else []
        figure_id = f"figure-{len(entries) + 1}"
        dpi = context.dpi if context.output == "screen" and context.dpi else None
        paths = save(figure, context.figure_dir / figure_id, formats=FORMATS[context.output], dpi=dpi)
        width, height = (value * 25.4 for value in figure.figure.get_size_inches())
        alt = ". ".join(part for part in (figure.title, figure.subtitle) if part)
        entries.append({"id": figure_id, "files": {path.suffix[1:]: str(path) for path in paths},
                        "width_mm": round(width, 2), "height_mm": round(height, 2), "alt": alt})
        manifest_path.write_text(json.dumps(entries, indent=1), encoding="utf-8")
        figure.handed_off = True
    finally:
        _state["handing_off"] = False
