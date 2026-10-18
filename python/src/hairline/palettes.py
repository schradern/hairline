"""Colours: categorical palettes and purpose sets for groups, ramps for amounts.

hairline picks colours for you; these functions show and change them.

- `palettes()` lists every colour set with its kind, number of colours, use and which one is active;
  `swatches()` draws them.
- Groups take a palette's colours in order: two groups the first two, three the first three, and a group keeps
  its colour when more are shown. Six palettes of eight colours: "daylight" (the default), "bloom", "citrus",
  "lagoon", "calm", "deep". Purpose sets: "pair", "pair-teal", "pair-violet" (two groups), "ink" (greyscale
  print), "judgement" (low, some concerns, high). `use(palette="calm")` makes one the default.
- Amounts take a ramp: "blues", "teals", "oranges", "berries", "greys" (sequential), "blue-coral", "teal-berry"
  (diverging). `colormap()` turns one into a matplotlib colormap. While a brand is active, its own ramps
  "brand-sequential" and "brand-diverging" are the default for `ramp()`, `colormap()` and the heatmap.
- Colours follow names across charts: `use(colors={"Unit B": "#e8a628"})` pins them, `color()` reads them; a
  brand file can hold the palette and the pinned colours. `check_palette()` measures your own colours.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from hairline.color.check import check_palette
from hairline.color.space import hex_to_oklab, linear_to_hex, oklab_to_linear, parse_hex
from hairline.tokens import load_tokens

PURPOSE_SETS = ("pair", "pair-teal", "pair-violet", "ink", "judgement")
JUDGEMENT_ORDER = ("low", "some", "high")
KINDS = ("categorical", "purpose", "sequential", "diverging")


def named_colors(name: str) -> list[str] | None:
    """A palette or purpose set by name (judgement in its order: low, some concerns, high)."""
    tokens = load_tokens()
    if name in tokens["palettes"]:
        return list(tokens["palettes"][name])
    if name == "judgement":
        return [tokens["sets"]["judgement"][level] for level in JUDGEMENT_ORDER]
    return list(tokens["sets"][name]) if name in PURPOSE_SETS else None


def resolve_colors(name: str | Sequence[str] | None) -> tuple[str, list[str]]:
    tokens = load_tokens()
    if name is None:
        from hairline.settings import current_settings
        active = current_settings()
        return active.palette_label, list(active.palette)
    if isinstance(name, str):
        colors = named_colors(name)
        if colors is None and name in tokens["ramps"]:
            raise ValueError(f"hairline: {name!r} is a ramp, not a palette; use ramp({name!r}) or a continuous "
                             "colour scale")
        if colors is None:
            known = ", ".join([*tokens["palettes"], *PURPOSE_SETS])
            raise ValueError(f"hairline: unknown palette {name!r}; available palettes: {known}")
        return f"palette {name!r}", colors
    colors = list(name)
    for color in colors:
        parse_hex(color)
    return "custom palette", colors


def palette(name: str | Sequence[str] | None = None, n: int | None = None) -> list[str]:
    """Colours for groups, in the order hairline assigns them: two groups take slots 1-2, three groups slots 1-3,
    and a group keeps its colour when more are shown; `n` takes the first n slots and never repeats colours.

    Six categorical palettes of eight slots: "daylight" (the default), "bloom", "citrus", "lagoon", "calm" and
    "deep". Purpose sets: "pair", "pair-teal" and "pair-violet" for two groups, "ink" for greyscale print,
    "judgement" for low, some concerns and high. `None` gives the active palette; a list of hex colours is checked
    and returned. `palettes()` lists every set with its use, `swatches()` draws them, and `use(palette=...)`
    makes one the default. For amounts, use `ramp()`."""
    label, colors = resolve_colors(name)
    if n is None:
        return colors
    if n > len(colors):
        raise ValueError(f"hairline: {label} has {len(colors)} slots but {n} categories were given; "
                         "fold small categories into 'Other' or split the figure into panels")
    return colors[:n]


def light_slots(colors: Sequence[str], surface: str | None = None) -> list[int]:
    """1-based slots below 3:1 contrast against the surface."""
    return check_palette(colors, surface or load_tokens()["neutral"]["surface"]).light_slots


def interpolate(colors: Sequence[str], count: int) -> list[str]:
    points = [hex_to_oklab(color) for color in colors]
    result = []
    for index in range(count):
        position = index * (len(points) - 1) / max(count - 1, 1)
        low = min(int(position), len(points) - 2)
        weight = position - low
        mixed = [a + (b - a) * weight for a, b in zip(points[low], points[low + 1], strict=True)]
        result.append(linear_to_hex(*oklab_to_linear(*mixed)))
    return result


def ramp(name: str | None = None, n: int | None = None) -> list[str]:
    """Colours for amounts. Sequential ramps run light to dark in one hue ("blues", "teals", "oranges",
    "berries", "greys"); diverging ramps run from one pole through a neutral midpoint to the other ("blue-coral",
    "teal-berry"), for values below and above a reference. `n` other than the stored 7 (or 13) interpolates in
    OKLab. While a brand is active, "brand-sequential" and "brand-diverging" follow its colours, and `None` (the
    default) gives "brand-sequential", else "blues". `colormap()` turns a ramp into a matplotlib colormap;
    `palettes()` lists them all."""
    ramps = active_ramps()
    name = default_ramp() if name is None else name
    if name not in ramps and named_colors(name) is not None:
        raise ValueError(f"hairline: {name!r} is a palette, not a ramp; use palette({name!r}) for groups")
    if name not in ramps:
        raise ValueError(f"hairline: unknown ramp {name!r}; available ramps: {', '.join(ramps)}")
    colors = list(ramps[name])
    return colors if n is None or n == len(colors) else interpolate(colors, n)


BRAND_RAMPS = ("brand-sequential", "brand-diverging")


def active_ramps() -> dict[str, list[str]]:
    """The token ramps, and while a brand is active its own two."""
    from hairline.settings import current_settings
    return {**{name: list(colors) for name, colors in load_tokens()["ramps"].items()},
            **{name: list(colors) for name, colors in current_settings().ramps.items()}}


def default_ramp(kind: str = "sequential") -> str:
    """The ramp used where none is named: the brand's while one is active, else blues and the heatmap's."""
    brand = "brand-sequential" if kind == "sequential" else "brand-diverging"
    if brand in active_ramps():
        return brand
    return "blues" if kind == "sequential" else load_tokens()["correlation"]["ramp"]


def ramp_kind(name: str) -> str:
    diverging = {*load_tokens()["ramp_definitions"]["diverging"], "brand-diverging"}
    return "diverging" if name in diverging else "sequential"


def swatch_rows(names: Sequence[str] | None = None) -> list[dict]:
    """Colour sets as rows (name, kind, use, colours), grouped by kind in catalogue order."""
    tokens = load_tokens()
    every = [*tokens["palettes"], *PURPOSE_SETS, *active_ramps()]
    unknown = [name for name in names or () if name not in every]
    if unknown:
        raise ValueError(f"hairline: unknown colour set {unknown[0]!r}; use one of {', '.join(every)}")
    chosen = every if names is None else [name for name in every if name in names]
    rows = []
    for name in chosen:
        kind = "categorical" if name in tokens["palettes"] else "purpose" if name in PURPOSE_SETS else ramp_kind(name)
        colors = named_colors(name) if kind in ("categorical", "purpose") else ramp(name)
        rows.append({"name": name, "kind": kind, "use": tokens["colour_notes"][name], "colors": colors})
    return sorted(rows, key=lambda row: KINDS.index(row["kind"]))


def palettes(kind: str | None = None) -> pd.DataFrame:
    """Every colour set: palettes and purpose sets for groups, ramps for amounts; `active` marks the one in use.
    A palette from a brand or `use(palette=[...])` comes first. `kind` keeps one of categorical, purpose,
    sequential or diverging."""
    if kind is not None and kind not in KINDS:
        raise ValueError(f"hairline: unknown kind {kind!r}; use one of {', '.join(KINDS)}")
    from hairline.settings import current_settings
    active = current_settings()
    rows = [{"name": row["name"], "kind": row["kind"], "slots": len(row["colors"]),
             "active": row["kind"] in ("categorical", "purpose") and row["name"] == active.palette_name,
             "use": row["use"], "colors": " ".join(row["colors"])} for row in swatch_rows()]
    if named_colors(active.palette_name) is None:
        rows.insert(0, {"name": active.palette_name, "kind": "categorical", "slots": len(active.palette),
                        "active": True, "use": f"the active {active.palette_label}",
                        "colors": " ".join(active.palette)})
    table = pd.DataFrame(rows, columns=["name", "kind", "slots", "active", "use", "colors"])
    return table if kind is None else table[table["kind"] == kind].reset_index(drop=True)


def colormap(name: str | None = None, n: int | None = None, reverse: bool = False) -> LinearSegmentedColormap:
    """A ramp as a matplotlib colormap, for `imshow`, `pcolormesh` or `scatter(c=...)`; `reverse` flips it. `None`
    gives the default ramp (the brand's while one is active)."""
    name = default_ramp() if name is None else name
    colors = ramp(name, n)
    return LinearSegmentedColormap.from_list(f"{name}_r" if reverse else name, colors[::-1] if reverse else colors)
