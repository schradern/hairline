"""Register the bundled font with matplotlib and resolve requested families."""

from __future__ import annotations

import logging
import warnings
from collections.abc import Sequence
from importlib import resources

from matplotlib import font_manager

from hairline.tokens import load_tokens

_state = {"registered": False, "warned": set(), "weights": {}}
UPRIGHT = ("normal",)


def register_fonts() -> None:
    """Make the bundled 'Hairline Sans' files available to matplotlib (idempotent)."""
    if _state["registered"]:
        return
    folder = resources.files("hairline") / "data" / "fonts"
    logging.getLogger("matplotlib.font_manager").addFilter(FallbackWeightFilter())
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


def nearest_weight(requested: int, available: Sequence[int]) -> int:
    """The weight a browser takes from `available` for `requested` (CSS font matching): from 400 to 500 the
    requested weight up to 500, then lighter, then heavier; below 400 lighter first; above 500 heavier first.
    Weight 600 of a family with 400 and 700 is 700."""
    if not available or requested in available:
        return requested
    lighter = sorted((weight for weight in available if weight < requested), reverse=True)
    heavier = sorted(weight for weight in available if weight > requested)
    if 400 <= requested <= 500:
        up_to_500 = [weight for weight in heavier if weight <= 500]
        return (up_to_500 + lighter + [weight for weight in heavier if weight > 500])[0]
    return (lighter + heavier)[0] if requested < 400 else (heavier + lighter)[0]


def family_weights(family: str) -> list[int]:
    """Weights of the upright faces matplotlib knows for `family`, read once per family and font list."""
    register_fonts()
    entries = font_manager.fontManager.ttflist
    key = (family, len(entries))
    if key not in _state["weights"]:
        _state["weights"][key] = sorted({font_manager.weight_dict.get(entry.weight, entry.weight) for entry in entries
                                         if entry.name == family and entry.style in UPRIGHT})
    return _state["weights"][key]


def face_weight(family: str, requested: int) -> int:
    """The weight of the face `family` has for `requested`, so text is measured and drawn in a face that exists
    and matplotlib never falls back on its own (a semibold title in Helvetica Neue is its bold)."""
    return nearest_weight(requested, family_weights(family))


class FallbackWeightFilter(logging.Filter):
    """matplotlib logs each time the fallback lacks a weight (DejaVu Sans has no semibold) and takes the nearest;
    that is expected for the few glyphs it supplies, so the notice is dropped. Other font messages pass."""

    def filter(self, record: logging.LogRecord) -> bool:
        fallback = load_tokens()["font"]["fallback"]
        return not (record.getMessage().startswith("findfont: Failed to find font weight") and fallback in
                    record.getMessage())


def families(font: str) -> list[str]:
    """The font, then the fallback that ships with matplotlib (DejaVu Sans), which matplotlib takes glyph by glyph
    for characters the font lacks: the bundled font has no Greek letters (α, β, Δ, χ)."""
    fallback = load_tokens()["font"]["fallback"]
    return [font] if font == fallback else [font, fallback]
