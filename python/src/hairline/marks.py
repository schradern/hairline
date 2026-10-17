"""Series colours and mark styles: light-slot treatment and point density."""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib as mpl
from matplotlib.collections import PathCollection
from matplotlib.colors import to_hex

from hairline.color.space import hex_to_oklch, oklch_to_hex
from hairline.color.vision import contrast
from hairline.palettes import light_slots, palette
from hairline.settings import Settings, current_settings
from hairline.tokens import load_tokens


def series_colors(categories: Sequence[str], palette_name: str | Sequence[str] | None = None) -> dict[str, str]:
    """Map categories to palette slots in order; never repeats a colour."""
    colors = palette(palette_name, n=len(categories))
    return dict(zip(categories, colors, strict=True))


def surface_of(settings: Settings) -> str:
    return settings.neutral["surface"] if settings.background != "transparent" else "#ffffff"


def is_light(color: str, settings: Settings) -> bool:
    return light_slots([color], surface_of(settings)) == [1]


def point_fill(color: str, surface: str) -> str:
    """The colour itself, or for a light slot a darker shade of its hue that reaches 3:1 against the surface."""
    limit, step = load_tokens()["checks"]["contrast_light_slot"], load_tokens()["points"]["fill_lightness_step"]
    lightness, chroma, hue = hex_to_oklch(color)
    fill = color
    while contrast(fill, surface) < limit and lightness > 0:
        lightness = max(0.0, lightness - step)
        fill = oklch_to_hex(lightness, chroma, hue)
    return fill


def point_step(count: int) -> tuple[float, float]:
    """Radius (times base size) and opacity for a layer of `count` points in one panel."""
    for step in load_tokens()["points"]["steps"]:
        if step["max"] is None or count <= step["max"]:
            return step["radius"], step["opacity"]
    raise ValueError("hairline: tokens points.steps needs a last step with max null")


def line_style(color: str, settings: Settings | None = None) -> dict[str, object]:
    """Line width for a series; light slots are drawn 1.3x heavier."""
    settings, lines = settings or current_settings(), load_tokens()["lines"]
    width = lines["data"] * settings.base_size
    return {"color": color, "linewidth": width * (lines["light_slot_line"] if is_light(color, settings) else 1)}


def point_style(color: str, settings: Settings | None = None, count: int = 1) -> dict[str, object]:
    """Marker style for a series of `count` points: no outline, light slots filled darker, size by density."""
    settings = settings or current_settings()
    radius, opacity = point_step(count)
    return {"color": point_fill(color, surface_of(settings)), "markersize": 2 * radius * settings.base_size,
            "markeredgewidth": 0, "alpha": opacity}


SECONDARY_ID = "hairline-secondary"


def treat_line(line, settings: Settings) -> None:
    if line.get_gid() == SECONDARY_ID:
        return
    color = to_hex(line.get_color())
    if is_light(color, settings):
        line.set_linewidth(line.get_linewidth() * load_tokens()["lines"]["light_slot_line"])


def is_default_size(collection) -> bool:
    sizes = collection.get_sizes()
    return len(sizes) == 1 and abs(sizes[0] - mpl.rcParams["lines.markersize"] ** 2) < 1e-9


def fill_collection(collection, settings: Settings) -> None:
    """Light faces take their darker fill; collections coloured through a colour map keep theirs."""
    faces = collection.get_facecolor()
    if collection.get_array() is None and len(faces):
        surface = surface_of(settings)
        collection.set_facecolor([point_fill(to_hex(face), surface) for face in faces])


def size_collection(collection, settings: Settings) -> None:
    """No outline on filled points; size and opacity follow the count unless the plot set them."""
    faces = collection.get_facecolor()
    if not len(faces) or all(face[3] == 0 for face in faces):
        return
    collection.set_linewidth(0)
    radius, opacity = point_step(len(collection.get_offsets()))
    if is_default_size(collection):
        collection.set_sizes([(2 * radius * settings.base_size) ** 2])
    if collection.get_alpha() is None:
        collection.set_alpha(opacity)


def apply_light_slots(axes, settings: Settings, done: set[int], sized: set[int]) -> None:
    """Give light-slot lines and points their cue once, and size every point set by its count (as in R)."""
    for ax in axes:
        for line in ax.lines:
            if id(line) not in done:
                done.add(id(line))
                treat_line(line, settings)
        for collection in ax.collections:
            if not isinstance(collection, PathCollection):
                continue
            if id(collection) not in done:
                done.add(id(collection))
                fill_collection(collection, settings)
            if id(collection) not in sized:
                sized.add(id(collection))
                size_collection(collection, settings)
