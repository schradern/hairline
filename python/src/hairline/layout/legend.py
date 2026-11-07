"""Legend row: items from axes or explicit, packed into rows that wrap at the right edge."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from matplotlib.collections import PathCollection
from matplotlib.colors import to_hex
from matplotlib.container import BarContainer
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from hairline.layout.draw import add_line, add_polygon, add_rect, add_text
from hairline.layout.measure import text_width
from hairline.tokens import load_tokens

KINDS = ("line", "thin", "dash", "band", "dot", "square", "diamond")
# An open marker's outline (the mean's diamond) as a share of the data line width.
OPEN_EDGE = 0.6
# A key's title: text without a swatch (the binned colour key of legend_ramp()).
TITLE = "title"


@dataclass(frozen=True)
class LegendItem:
    kind: str
    color: str
    label: str
    outline: bool = False


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
    if isinstance(handle, BarContainer) and len(handle.patches):
        return LegendItem("square", to_hex(handle.patches[0].get_facecolor()), label)
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
    if kind == TITLE:
        return 0.0
    factor = spacing["legend_swatch_square"] if kind in ("dot", "square", "diamond") else spacing["legend_swatch_line"]
    return factor * base


def item_width(item: LegendItem, style: dict, spacing: dict) -> float:
    """Swatch, gap and label; a title is its text alone."""
    base, label = style["base"], text_width(item.label, style["family"], style["size"])
    if item.kind == TITLE:
        return label
    return swatch_width(item.kind, base, spacing) + spacing["legend_swatch_text"] * base + label


def pack_rows(items: Sequence[LegendItem], left: float, right: float, style: dict, spacing: dict,
              key: Sequence[LegendItem] = ()) -> list[PlacedItem]:
    """Place items left to right; start a new row when the next item would cross `right`. The `key` (a binned
    colour key) sits right-aligned on the first row, and the items keep clear of it there."""
    base, placed, row, cursor = style["base"], [], 0, left
    gap = spacing["legend_item"] * base
    widths = [item_width(item, style, spacing) for item in key]
    key_width = sum(widths) + gap * (len(widths) - 1) if widths else 0.0
    for item in items:
        width = item_width(item, style, spacing)
        edge = right - key_width - gap if row == 0 and key_width else right
        if cursor > left and cursor + width > edge:
            row, cursor = row + 1, left
        placed.append(PlacedItem(item, row, cursor, cursor + width))
        cursor += width + gap
    x = right - key_width
    for item, width in zip(key, widths, strict=True):
        placed.append(PlacedItem(item, 0, x, x + width))
        x += width + gap
    return placed


def draw_swatch(fig: Figure, item: LegendItem, x: float, center: float, base: float, spacing: dict,
                lines: dict) -> list:
    width = swatch_width(item.kind, base, spacing)
    if item.kind == TITLE:
        return []
    if item.kind == "diamond":
        half = width / 2
        points = [(x, center), (x + half, center - half), (x + width, center), (x + half, center + half)]
        return [add_polygon(fig, points, lines.get("surface", "#ffffff"), item.color, lines["data"] * base * OPEN_EDGE)]
    if item.kind in ("square", "dot", "band"):
        side = width if item.kind != "band" else swatch_width("square", base, spacing)
        edge = load_tokens()["legend_ramp"]["outline"] * base if item.outline else 0.0
        return [add_rect(fig, x, center - side / 2, width if item.kind == "band" else side, side, item.color,
                         lines.get("outline_color") if item.outline else None, edge)]
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
        if entry.item.kind == TITLE:
            text_x = entry.x
        artists.append(add_text(fig, text_x, center + style["size"] * cap / 2, entry.item.label, style))
    return artists


def ramp_key_items(key: dict | None) -> list[LegendItem]:
    """The binned colour key as legend items: its title, then one outlined square per step."""
    if key is None:
        return []
    items = [LegendItem(TITLE, "#000000", key["title"])] if key.get("title") else []
    return items + [LegendItem("square", color, label, outline=True)
                    for color, label in zip(key["colors"], key["labels"], strict=True)]
