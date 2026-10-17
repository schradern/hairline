"""Entity colours: one colour per entity for the whole session."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

_state: dict[str, dict[str, str]] = {"fixed": {}, "auto": {}}


def assign_colors(palette: Sequence[str], label: str, fixed: Mapping[str, str],
                  requests: Sequence[str]) -> dict[str, str]:
    """Colours for `requests`: fixed ones as given, new ones the first free palette slot in slot order."""
    mapping, taken = dict(fixed), set(fixed.values())
    for name in requests:
        if name in mapping:
            continue
        free = [color for color in palette if color not in taken]
        if not free:
            names = list(dict.fromkeys([*mapping, *requests]))
            raise ValueError(f"hairline: {label} has {len(palette)} slots but {len(names)} categories need colours: "
                             f"{', '.join(names)}; fold small categories into 'Other' or split the figure into panels")
        mapping[name] = free[0]
        taken.add(free[0])
    return {name: mapping[name] for name in requests}


def configure(fixed: Mapping[str, str]) -> None:
    """Start a new assignment with these fixed colours (explicit and brand mappings)."""
    _state["fixed"] = dict(fixed)
    _state["auto"] = {}


def color(name: str) -> str:
    """The entity's colour, assigning the next free palette slot on first use."""
    from hairline.settings import current_settings
    known = {**_state["fixed"], **_state["auto"]}
    if name in known:
        return known[name]
    settings = current_settings()
    _state["auto"][name] = assign_colors(settings.palette, settings.palette_label, known, [name])[name]
    return _state["auto"][name]


def colors() -> dict[str, str]:
    """Every entity colour fixed or assigned so far in this session."""
    return {**_state["fixed"], **_state["auto"]}
