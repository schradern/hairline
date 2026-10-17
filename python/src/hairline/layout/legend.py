"""Legend row: items from axes or explicit, packed into rows that wrap at the right edge."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from matplotlib.collections import PathCollection
from matplotlib.colors import to_hex
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from hairline.layout.draw import add_line, add_rect, add_text
from hairline.layout.measure import text_width

KINDS = ("line", "thin", "dash", "band", "dot", "square")


@dataclass(frozen=True)
class LegendItem:
    kind: str
    color: str
    label: str


@dataclass(frozen=True)
class PlacedItem:
    item: LegendItem
    row: int
    x: float
    right: float


def item_from_handle(handle: object, label: str) -> LegendItem | None:
    if isinstance(handle, Line2D):
        kind = "dash" if handle.get_linestyle() in ("--", "dashed", ":", "dotted") else "line"
        if handle.get_linestyle() in ("None", "none", "") and handle.get_marker() not in ("None", None, ""):
            kind = "dot"
        return LegendItem(kind, to_hex(handle.get_color()), label)
    if isinstance(handle, PathCollection):
        return LegendItem("dot", to_hex(handle.get_facecolor()[0]), label)
    if isinstance(handle, Patch):
        return LegendItem("square", to_hex(handle.get_facecolor()), label)
    return None


def items_from_axes(axes: Sequence) -> list[LegendItem]:
    """Legend items from labelled artists, first occurrence of each label, in drawing order."""
    items, seen = [], set()
    for ax in axes:
        handles, labels = ax.get_legend_handles_labels()
        for handle, label in zip(handles, labels, strict=True):
            item = item_from_handle(handle, label)
            if item and label not in seen:
                seen.add(label)
                items.append(item)
    return items


def validate_items(items: Sequence[tuple[str, str, str]]) -> list[LegendItem]:
    result = []
    for kind, color, label in items:
        if kind not in KINDS:
            raise ValueError(f"hairline: unknown legend kind {kind!r} for {label!r}; use one of {', '.join(KINDS)}")
        result.append(LegendItem(kind, to_hex(color), label))
    return result


def swatch_width(kind: str, base: float, spacing: dict) -> float:
    factor = spacing["legend_swatch_square"] if kind in ("dot", "square") else spacing["legend_swatch_line"]
    return factor * base


def pack_rows(items: Sequence[LegendItem], left: float, right: float, style: dict, spacing: dict) -> list[PlacedItem]:
    """Place items left to right; start a new row when the next item would cross `right`."""
    base, placed, row, cursor = style["base"], [], 0, left
    for item in items:
        width = (swatch_width(item.kind, base, spacing) + spacing["legend_swatch_text"] * base
                 + text_width(item.label, style["family"], style["size"]))
        if cursor > left and cursor + width > right:
            row, cursor = row + 1, left
        placed.append(PlacedItem(item, row, cursor, cursor + width))
        cursor += width + spacing["legend_item"] * base
    return placed


def draw_swatch(fig: Figure, item: LegendItem, x: float, center: float, base: float, spacing: dict,
                lines: dict) -> list:
    width = swatch_width(item.kind, base, spacing)
    if item.kind in ("square", "dot", "band"):
        side = width if item.kind != "band" else swatch_width("square", base, spacing)
        return [add_rect(fig, x, center - side / 2, width if item.kind == "band" else side, side, item.color)]
    style = {"color": item.color, "width": lines["data"] * base}
    if item.kind == "thin":
        style = {"color": item.color, "width": lines["secondary"] * base * 2, "alpha": lines["secondary_opacity"] + 0.2}
    if item.kind == "dash":
        style = {**style, "width": lines["reference"] * base, "dash": (0, tuple(lines["reference_dash"]))}
    return [add_line(fig, x, center, x + width, center, style)]


def draw_legend(fig: Figure, placed: Sequence[PlacedItem], centers: Sequence[float], style: dict,
                spacing: dict, lines: dict) -> list:
    artists, base = [], style["base"]
    cap = style["cap_height"]
    for entry in placed:
        center = centers[entry.row]
        artists += draw_swatch(fig, entry.item, entry.x, center, base, spacing, lines)
        text_x = entry.x + swatch_width(entry.item.kind, base, spacing) + spacing["legend_swatch_text"] * base
        artists.append(add_text(fig, text_x, center + style["size"] * cap / 2, entry.item.label, style))
    return artists
