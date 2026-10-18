"""Entity colours: per chart, groups take the colour set for their count; a name keeps
its colour across charts unless that would clash within one chart."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager

_state: dict[str, dict[str, str]] = {"fixed": {}, "auto": {}}
_scopes: list[dict[str, str]] = []


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


def chart_colors(palette: Sequence[str], label: str, fixed: Mapping[str, str], remembered: Mapping[str, str],
                 override: Mapping[str, str], names: Sequence[str]) -> dict[str, str]:
    """Colours for one chart: the chart's own override, then fixed colours, then a name's remembered colour unless
    another group in this chart already has it, then the first slot still free in this chart."""
    names = list(dict.fromkeys(names))
    result = {name: override.get(name, fixed.get(name)) for name in names if name in override or name in fixed}
    used = set(result.values())
    for name in names:
        if name not in result and remembered.get(name) and remembered[name] not in used:
            result[name] = remembered[name]
            used.add(result[name])
    for name in names:
        if name in result:
            continue
        free = [color for color in palette if color not in used]
        if not free:
            raise ValueError(f"hairline: {label} has {len(palette)} slots but {len(names)} categories need colours: "
                             f"{', '.join(names)}; fold small categories into 'Other' or split the figure into panels")
        result[name] = free[0]
        used.add(free[0])
    return {name: result[name] for name in names}


@contextmanager
def chart(names: Sequence[str], colors: Mapping[str, str] | None = None) -> Iterator[dict[str, str]]:
    """Assign the colours of one chart's groups at once; inside, color(name) answers from this assignment."""
    from hairline.settings import current_settings
    settings, override = current_settings(), {name: str(value).lower() for name, value in (colors or {}).items()}
    mapping = chart_colors(settings.palette, settings.palette_label, _state["fixed"], _state["auto"], override,
                           [str(name) for name in names])
    for name, value in mapping.items():
        if name not in override and name not in _state["fixed"] and name not in _state["auto"]:
            _state["auto"][name] = value
    _scopes.append(mapping)
    try:
        yield mapping
    finally:
        _scopes.pop()


def colors_for(names: Sequence[str], colors: Mapping[str, str] | None = None) -> dict[str, str]:
    """The colours of one chart's groups, assigned as chart() does."""
    with chart(names, colors) as mapping:
        return dict(mapping)


def configure(fixed: Mapping[str, str]) -> None:
    """Start a new assignment with these fixed colours (explicit and brand mappings)."""
    _state["fixed"] = dict(fixed)
    _state["auto"] = {}


def color(name: str) -> str:
    """The entity's colour: from the chart being drawn, else remembered, else the next free palette slot."""
    from hairline.settings import current_settings
    if _scopes and name in _scopes[-1]:
        return _scopes[-1][name]
    known = {**_state["fixed"], **_state["auto"]}
    if name in known:
        return known[name]
    settings = current_settings()
    _state["auto"][name] = assign_colors(settings.palette, settings.palette_label, known, [name])[name]
    return _state["auto"][name]


def colors() -> dict[str, str]:
    """Every entity colour fixed or assigned so far in this session."""
    return {**_state["fixed"], **_state["auto"]}
