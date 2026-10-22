"""Entity colours from a brand: pinned colours checked like a palette (every pair), and section groups whose
members take tints of the section's colour."""

from __future__ import annotations

import itertools
import warnings

from hairline.color.adapt import adapt_readable
from hairline.color.tints import tints
from hairline.color.vision import delta_e
from hairline.tokens import load_tokens


def pair_failures(colors: dict[str, str]) -> list[str]:
    """Pairs of pinned colours that colour-blind or normal vision cannot tell apart."""
    limits, failures = load_tokens()["checks"], []
    for (first, one), (second, two) in itertools.combinations(colors.items(), 2):
        vision = min(delta_e(one, two, "protan"), delta_e(one, two, "deutan"))
        normal = delta_e(one, two)
        if vision < limits["cvd_floor"]:
            failures.append(f"{first} / {second}: colour-vision ΔE {vision:.1f} is below {limits['cvd_floor']}")
        elif normal < limits["normal_floor"]:
            failures.append(f"{first} / {second}: normal-vision ΔE {normal:.1f} is below "
                            f"{limits['normal_floor']}")
    return failures


def checked_entities(colors: dict[str, str], mode: str, label: str) -> tuple[dict[str, str], list[str]]:
    """Readable mode steps failing pinned colours (all pairs); exact mode keeps them and warns."""
    failures = pair_failures(colors)
    if not failures or len(colors) < 2:
        return colors, failures
    if mode == "readable":
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            adapted = dict(zip(colors, adapt_readable(list(colors.values()), pairs="all"), strict=True))
        return adapted, pair_failures(adapted)
    warnings.warn(f"hairline: {label}: pinned colours are hard to tell apart: {'; '.join(failures)}", UserWarning,
                  stacklevel=4)
    return colors, failures


def grouped_entities(colors: dict[str, str], groups: dict, fail) -> dict[str, str]:
    """Members of a group without their own colour take tints of the group's colour, in listed order."""
    result = dict(colors)
    for group, members in (groups or {}).items():
        key = f"defaults.hairline.groups.{group}"
        if group not in colors:
            raise fail(key, f"group {group!r} needs a colour in defaults.hairline.colors")
        members = [members] if isinstance(members, (str, int, float)) else members
        if not isinstance(members, list) or not members:
            raise fail(key, "must list the group's members")
        for member, shade in zip(members, tints(colors[group], len(members)), strict=True):
            result.setdefault(str(member), shade)
    return result
