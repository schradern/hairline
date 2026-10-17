"""Palette checks: lightness band, chroma floor, colour-vision separation, normal vision, light slots."""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from hairline.color.space import hex_to_oklch, parse_hex
from hairline.color.vision import contrast, delta_e
from hairline.tokens import load_tokens

NO_PAIRS = 100.0


@dataclass(frozen=True)
class PaletteReport:
    passed: bool
    worst_cvd: float
    worst_normal: float
    head_all_pairs: float
    light_slots: list[int]
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


def pair_indices(count: int, pairs: Literal["adjacent", "all"]) -> list[tuple[int, int]]:
    if pairs == "all":
        return list(itertools.combinations(range(count), 2))
    return [(index, index + 1) for index in range(count - 1)]


def worst_cvd(colors: Sequence[str], indices: list[tuple[int, int]]) -> float:
    distances = [delta_e(colors[a], colors[b], kind) for a, b in indices for kind in ("protan", "deutan")]
    return min(distances, default=NO_PAIRS)


def worst_normal(colors: Sequence[str], indices: list[tuple[int, int]]) -> float:
    return min((delta_e(colors[a], colors[b]) for a, b in indices), default=NO_PAIRS)


def band_failures(colors: Sequence[str], limits: dict) -> list[str]:
    low, high = limits["lightness"]
    failures = [f"lightness: slot {index} {color} has L {hex_to_oklch(color)[0]:.3f}, outside {low}–{high}"
                for index, color in enumerate(colors, start=1) if not low <= hex_to_oklch(color)[0] <= high]
    failures += [f"chroma: slot {index} {color} has C {hex_to_oklch(color)[1]:.3f}, below {limits['chroma_floor']}"
                 for index, color in enumerate(colors, start=1) if hex_to_oklch(color)[1] < limits["chroma_floor"]]
    return failures


def grade(value: float, label: str, limits: dict, failures: list[str], warnings: list[str]) -> None:
    if value < limits["cvd_floor"]:
        failures.append(f"{label}: worst colour-vision ΔE {value:.1f} is below {limits['cvd_floor']}")
    elif value < limits["cvd_target"]:
        warnings.append(f"{label}: worst colour-vision ΔE {value:.1f} is below {limits['cvd_target']}; "
                        "use labels or gaps as a second cue")


def check_palette(colors: Sequence[str], surface: str = "#ffffff",
                  pairs: Literal["adjacent", "all"] = "adjacent") -> PaletteReport:
    """Run hairline's palette checks."""
    colors = list(colors)
    for color in [*colors, surface]:
        parse_hex(color)
    limits = load_tokens()["checks"]
    failures, warnings = band_failures(colors, limits), []
    cvd = worst_cvd(colors, pair_indices(len(colors), pairs))
    normal = worst_normal(colors, pair_indices(len(colors), pairs))
    head = worst_cvd(colors[: limits["head_slots"]], pair_indices(min(len(colors), limits["head_slots"]), "all"))
    grade(cvd, f"{pairs} pairs", limits, failures, warnings)
    grade(head, f"first {limits['head_slots']} slots", limits, failures, warnings)
    if normal < limits["normal_floor"]:
        failures.append(f"normal vision: worst ΔE {normal:.1f} is below {limits['normal_floor']}")
    light = [index for index, color in enumerate(colors, start=1)
             if contrast(color, surface) < limits["contrast_light_slot"]]
    return PaletteReport(not failures, cvd, normal, head, light, warnings, failures)
