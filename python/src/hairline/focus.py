"""Guiding focus: highlight series or panels, reference lines with labels."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from matplotlib.collections import PathCollection
from matplotlib.colors import to_hex

from hairline.errors import HairlineLayoutError
from hairline.layout.legend import LegendItem
from hairline.settings import role_size
from hairline.tokens import load_tokens

if TYPE_CHECKING:
    from hairline.figure import HairlineFigure

REFERENCE_ID = "hairline-reference"


def data_artists(ax) -> list:
    lines = [line for line in ax.lines if line.get_gid() != REFERENCE_ID]
    return lines + [collection for collection in ax.collections if isinstance(collection, PathCollection)]


def series_labels(figure: HairlineFigure) -> list[str]:
    labels = [artist.get_label() for ax in figure.axes for artist in data_artists(ax)]
    return list(dict.fromkeys(label for label in labels if not label.startswith("_")))


def panel_indexes(figure: HairlineFigure, panels: Sequence[int | str]) -> set[int]:
    names = {header.name: index for index, header in figure.headers.items()}
    indexes = set()
    for panel in panels:
        if isinstance(panel, int) and 0 <= panel < len(figure.axes):
            indexes.add(panel)
        elif panel in names:
            indexes.add(names[panel])
        else:
            known = ", ".join(names) or "no panel names set"
            raise HairlineLayoutError(f"hairline: highlight: panel {panel!r} does not exist; panel names: {known}")
    return indexes


def check_series(figure: HairlineFigure, series: Sequence[str]) -> None:
    labels = series_labels(figure)
    for name in series:
        if name not in labels:
            raise HairlineLayoutError(f"hairline: highlight: {name!r} is not a series label; labels: "
                                      f"{', '.join(labels) or 'none'}")


def restyle(artist, keep: bool, rules: dict) -> None:
    if isinstance(artist, PathCollection):
        if not keep:
            artist.set_color(rules["context"])
        return
    artist.set_linewidth(artist.get_linewidth() * (rules["highlight_width"] if keep else rules["context_width"]))
    if not keep:
        artist.set_color(rules["context"])


def artist_color(artist) -> str:
    if isinstance(artist, PathCollection):
        faces = artist.get_facecolor()
        return to_hex(faces[0]) if len(faces) else ""
    return to_hex(artist.get_color())


def apply_entity_colors(figure: HairlineFigure) -> None:
    """Labelled series drawn in a palette colour take their entity's colour (custom colours stay)."""
    from hairline import entities
    palette = set(figure.settings.palette)
    for ax in figure.axes:
        for artist in data_artists(ax):
            label = artist.get_label()
            if id(artist) in figure.entity_done or label.startswith("_") or artist_color(artist) not in palette:
                continue
            figure.entity_done.add(id(artist))
            artist.set_color(entities.color(label))


def apply_highlight(figure: HairlineFigure) -> None:
    """Restyle every data artist once: highlighted ones heavier, the rest in context grey without light-slot cues."""
    spec = figure.highlight_spec
    if not spec:
        return
    rules = load_tokens()["focus"]
    if spec["series"]:
        check_series(figure, spec["series"])
    panels = panel_indexes(figure, spec["panels"]) if spec["panels"] else set(range(len(figure.axes)))
    for index, ax in enumerate(figure.axes):
        for artist in data_artists(ax):
            if id(artist) in figure.focus_done:
                continue
            figure.focus_done.add(id(artist))
            keep = index in panels and (not spec["series"] or artist.get_label() in spec["series"])
            restyle(artist, keep, rules)
            if not keep:
                figure.light_slot_done.add(id(artist))


def add_reference(figure: HairlineFigure, y: float | None, x: float | None, label: str | None,
                  panels: Sequence[int] | None, legend_label: str | None) -> None:
    if (y is None) == (x is None):
        raise ValueError("hairline: reference() needs exactly one of y= or x=")
    rules, base = load_tokens()["reference"], figure.settings.base_size
    style = {"color": rules["color"], "linewidth": rules["width"] * base, "linestyle": (0, tuple(rules["dash"])),
             "zorder": 1.5, "gid": REFERENCE_ID, "label": "_nolegend_"}
    for index in panels if panels is not None else range(len(figure.axes)):
        ax = figure.axes[index]
        ax.axhline(y, **style) if y is not None else ax.axvline(x, **style)
        if label:
            text = ax.annotate(label, xy=(1, y) if y is not None else (x, 1),
                               xycoords=("axes fraction", "data") if y is not None else ("data", "axes fraction"),
                               ha="right" if y is not None else "left", va="bottom" if y is not None else "top",
                               fontsize=role_size(figure.settings, "caption"), color=figure.settings.neutral["faint"],
                               fontfamily=figure.settings.font, annotation_clip=False)
            figure.references.append((ax, text, y))
    if legend_label:
        figure.extra_legend_items.append(LegendItem("dash", rules["color"], legend_label))


def label_goes_below(offset_from_top: float, size: float, base_size: float) -> bool:
    """Above the line unless the label's cap height would reach into the panel header's gap (same rule in R)."""
    tokens = load_tokens()
    gap = tokens["reference"]["label_gap"] * size
    cap = cap_height()
    return offset_from_top - gap - cap * size < -tokens["spacing"]["panel_header"] * base_size


def cap_height() -> float:
    from hairline.layout.geometry import load_font_metrics
    return load_font_metrics().cap_height


def place_reference_labels(figure: HairlineFigure) -> None:
    size = role_size(figure.settings, "caption")
    gap = load_tokens()["reference"]["label_gap"] * size
    for ax, text, y in figure.references:
        text.set_anncoords("offset points")
        if y is None:
            text.set_position((gap, -gap))
            continue
        low, high = ax.get_ylim()
        height_pt = ax.get_position().height * figure.figure.get_size_inches()[1] * 72
        below = label_goes_below((high - y) / (high - low) * height_pt, size, figure.settings.base_size)
        text.set_position((0, -gap if below else gap))
        text.set_va("top" if below else "bottom")


def focus_legend_items(figure: HairlineFigure, items: list[LegendItem]) -> list[LegendItem]:
    """Legend swatches show a series' highlighted colour, not the context grey of its other panels."""
    if not figure.highlight_spec:
        return items
    context = load_tokens()["focus"]["context"]
    colours = {}
    for ax in figure.axes:
        for artist in data_artists(ax):
            colour = to_hex(artist.get_color() if hasattr(artist, "get_linewidth") and not isinstance(
                artist, PathCollection) else artist.get_facecolor()[0])
            if colour != context:
                colours.setdefault(artist.get_label(), colour)
    return [LegendItem(item.kind, colours.get(item.label, item.color), item.label) for item in items]
