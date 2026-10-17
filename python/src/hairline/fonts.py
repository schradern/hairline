"""Register the bundled font with matplotlib and resolve requested families."""

from __future__ import annotations

import warnings
from importlib import resources

from matplotlib import font_manager

from hairline.tokens import load_tokens

_state = {"registered": False, "warned": set()}


def register_fonts() -> None:
    """Make the bundled 'Hairline Sans' files available to matplotlib (idempotent)."""
    if _state["registered"]:
        return
    folder = resources.files("hairline") / "data" / "fonts"
    for filename in load_tokens()["font"]["files"].values():
        path = folder / filename
        if not path.is_file():
            raise RuntimeError(f"hairline: bundled font file {filename} missing in {folder}; reinstall the package")
        font_manager.fontManager.addfont(str(path))
    _state["registered"] = True


def installed_families() -> set[str]:
    return {entry.name for entry in font_manager.fontManager.ttflist}


def resolve_family(requested: str | None) -> str:
    """Return `requested` when installed, else the bundled family (warning once per name)."""
    register_fonts()
    bundled = load_tokens()["font"]["family"]
    if requested is None or requested == bundled or requested in installed_families():
        return requested or bundled
    if requested not in _state["warned"]:
        _state["warned"].add(requested)
        warnings.warn(f"hairline: font '{requested}' is not installed; using '{bundled}'", UserWarning, stacklevel=3)
    return bundled
