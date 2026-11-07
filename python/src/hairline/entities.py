"""Entity colours: per chart, groups take the colour set for their count; a name keeps
its colour across charts unless that would clash within one chart."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager

_state: dict[str, dict[str, str]] = {"fixed": {}, "auto": {}, "dimensions": {}}
_scopes: list[dict[str, str]] = []
_dimensions: list[str | None] = []


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
                 override: Mapping[str, str], names: Sequence[str], reserved: Mapping[str, str] | None = None,
                 dimension: str | None = None, taken: Sequence[str] = ()) -> dict[str, str]:
    """Colours for one chart: the chart's own override, then fixed colours, then a name's remembered colour unless
    another group in this chart already has it, then the first slot still free in this chart. `reserved` maps the
    colours that names of other dimensions hold to those dimensions: a free slot is never one of them, so a figure
    of application patterns never reuses the blue a procedure has, as long as the palette has room."""
    names, reserved = list(dict.fromkeys(names)), dict(reserved or {})
    result = {name: override.get(name, fixed.get(name)) for name in names if name in override or name in fixed}
    used = set(result.values()) | set(taken)
    for name in names:
        if name not in result and remembered.get(name) and remembered[name] not in used:
            result[name] = remembered[name]
            used.add(result[name])
    for name in names:
        if name in result:
            continue
        free = [color for color in palette if color not in used and color not in reserved]
        if not free:
            raise ValueError(no_room(palette, label, names, reserved, dimension))
        result[name] = free[0]
        used.add(free[0])
    return {name: result[name] for name in names}


def no_room(palette: Sequence[str], label: str, names: Sequence[str], reserved: Mapping[str, str],
            dimension: str | None) -> str:
    """The palette is full: either this chart's categories alone, or together with the slots another dimension
    holds (then both dimensions are named, so the reader knows which colours to pin or free)."""
    if reserved and len(names) <= len(palette):
        others = sorted({other for other in reserved.values()})
        return (f"hairline: {label} has {len(palette)} slots; {len(reserved)} are held by dimension "
                f"{', '.join(repr(other) for other in others)} and {len(names)} categories of dimension "
                f"{dimension!r} need colours: {', '.join(names)}; use fewer categories, pin colours with "
                f"use(colors=...) or give the dimensions one palette each")
    return (f"hairline: {label} has {len(palette)} slots but {len(names)} categories need colours: "
            f"{', '.join(names)}; fold small categories into 'Other' or split the figure into panels")


def reserved_colors(dimension: str | None) -> dict[str, str]:
    """Colours remembered for names of other dimensions than `dimension` (None: names given no dimension)."""
    known = {**_state["fixed"], **_state["auto"]}
    return {color: str(_state["dimensions"].get(name)) for name, color in known.items()
            if _state["dimensions"].get(name) != dimension}


def ordered_colors(names: Sequence[str], ramp_name: str) -> dict[str, str]:
    """Ordered groups (low, medium, high risk) as steps of one ramp in the chart's order: a sequential ramp from
    its middle to its dark end, so the lightest group still reads as a dot or a line on the surface; a diverging
    ramp across both poles."""
    from hairline.palettes import ramp, ramp_kind
    names = [str(name) for name in dict.fromkeys(names)]
    if ramp_kind(ramp_name) == "diverging":
        return dict(zip(names, ramp(ramp_name, len(names)), strict=True))
    return dict(zip(names, ramp(ramp_name, len(names) + 2)[2:], strict=True))


@contextmanager
def chart(names: Sequence[str], colors: Mapping[str, str] | str | None = None,
          dimension: str | None = None) -> Iterator[dict[str, str]]:
    """Assign the colours of one chart's groups at once; inside, color(name) answers from this assignment.
    `colors` maps names to colours, or names a ramp ("blues") for ordered groups. `dimension` names what the groups
    are (procedures, application patterns): groups of one dimension keep clear of the slots another dimension
    holds. Without one, the enclosing scope() applies."""
    from hairline.settings import current_settings
    colors = ordered_colors(names, colors) if isinstance(colors, str) else colors
    settings, override = current_settings(), {name: str(value).lower() for name, value in (colors or {}).items()}
    dimension = dimension if dimension is not None else current_dimension()
    mapping = chart_colors(settings.palette, settings.palette_label, _state["fixed"], _state["auto"], override,
                           [str(name) for name in names], reserved_colors(dimension), dimension)
    for name, value in mapping.items():
        if name not in override and name not in _state["fixed"] and name not in _state["auto"]:
            _state["auto"][name] = value
            if dimension is not None:
                _state["dimensions"][name] = dimension
    _scopes.append(mapping)
    try:
        yield mapping
    finally:
        _scopes.pop()


def colors_for(names: Sequence[str], colors: Mapping[str, str] | None = None,
               dimension: str | None = None) -> dict[str, str]:
    """The colours of one chart's groups, assigned as chart() does."""
    with chart(names, colors, dimension) as mapping:
        return dict(mapping)


@contextmanager
def scope(dimension: str) -> Iterator[None]:
    """Charts drawn inside take `dimension` for their groups: `with scope("pattern"): bars(...)` keeps the patterns
    off the slots the session's procedures hold, as `dimension="pattern"` on each chart would."""
    _dimensions.append(str(dimension))
    try:
        yield
    finally:
        _dimensions.pop()


def current_dimension() -> str | None:
    return _dimensions[-1] if _dimensions else None


def configure(fixed: Mapping[str, str]) -> None:
    """Start a new assignment with these fixed colours (explicit and brand mappings)."""
    _state["fixed"] = dict(fixed)
    _state["auto"] = {}
    _state["dimensions"] = {}


def color(name: str) -> str:
    """The entity's colour: from the chart being drawn, else remembered, else the next free palette slot."""
    from hairline.settings import current_settings
    if _scopes and name in _scopes[-1]:
        return _scopes[-1][name]
    known = {**_state["fixed"], **_state["auto"]}
    if name in known:
        return known[name]
    settings, dimension = current_settings(), current_dimension()
    free = [color for color in settings.palette if color not in reserved_colors(dimension)]
    if len(free) < len(settings.palette) and not [color for color in free if color not in known.values()]:
        raise ValueError(no_room(settings.palette, settings.palette_label, [name], reserved_colors(dimension),
                                 dimension))
    _state["auto"][name] = assign_colors(free, settings.palette_label, known, [name])[name]
    if current_dimension() is not None:
        _state["dimensions"][name] = current_dimension()
    return _state["auto"][name]


def colors() -> dict[str, str]:
    """Every entity colour fixed or assigned so far in this session."""
    return {**_state["fixed"], **_state["auto"]}
