"""Waffle chart: shares of a whole as a square grid of cells (10 x 10, one cell per percent), filled row by row from
the top left in the slices' order, with a key of names and shares beside it."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import pandas as pd

from hairline.alt_text import TIE_DIGITS
from hairline.charts.common import humanise, joined, with_counts
from hairline.charts.donut import donut_rings
from hairline.charts.donut_alt import donut_description
from hairline.charts.donut_geometry import Measure, hierarchical_key, key_right, key_rows, square
from hairline.charts.tips import tagged
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.layout.geometry import Box
from hairline.settings import current_settings
from hairline.tokens import load_tokens


def cell_counts(shares: Sequence[float], cells: int) -> list[int]:
    """Cells per slice by the largest remainder, so they always add up to `cells`; equal remainders go to the
    earlier slice. A slice under half a cell may get none."""
    exact = [share * cells for share in shares]
    counts = [math.floor(round(amount, TIE_DIGITS)) for amount in exact]
    remainders = [round(amount - count, TIE_DIGITS) for amount, count in zip(exact, counts, strict=True)]
    ranked = sorted(range(len(shares)), key=lambda index: (-remainders[index], index))
    for index in ranked[:cells - sum(counts)]:
        counts[index] += 1
    return counts


def cell_shapes(ring: list[dict], left: float, top: float, side: float, rules: dict) -> list[dict]:
    """One square per cell, row by row from the top left; each names its slice and share for the HTML tooltips."""
    per_row, gap = rules["side"], rules["gap_pt"]
    cell = (side - (per_row - 1) * gap) / per_row
    fills = [segment for segment, count in zip(ring, cell_counts([item["share"] for item in ring], per_row ** 2),
                                               strict=True) for _ in range(count)]
    return [tagged(square(left + (index % per_row) * (cell + gap), top + (index // per_row) * (cell + gap), cell,
                          segment["color"]), segment["name"], f"{segment['name']}: {segment['share_text']}")
            for index, segment in enumerate(fills)]


def grid_side(ring: list[dict], width: float, measure: Measure, style: dict, rules: dict, key_rules: dict) -> float:
    """A share of the panel width, smaller where the key needs the room for its names on one line, but never under
    `min_grid_share`: below that the key wraps its names instead."""
    key_width = key_right(key_rows([ring]), 0.0, math.inf, measure, style, key_rules)
    room = width - key_rules["key_gap"] * style["base"] - key_width
    return max(width * rules["min_grid_share"], min(width * rules["grid_share"], room))


def waffle_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    """The grid at the panel's top left and the key centred beside it."""
    rules, key_rules = load_tokens()["waffle"], load_tokens()["donut"]
    side = grid_side(spec["ring"], box.width, measure, style, rules, key_rules)
    key_left = box.x + side + key_rules["key_gap"] * style["base"]
    return cell_shapes(spec["ring"], box.x, box.y, side, rules) + hierarchical_key(
        [spec["ring"]], key_left, box, box.y + side / 2, measure, style, key_rules, "waffle")


def waffle(data: pd.DataFrame, label: str, value: str | None = None, *, title: str | None = None,
           subtitle: str | None = None, caption: str | None = None, colors: Mapping[str, str] | None = None,
           order: Sequence[str] | None = None, size: str = "onehalf") -> HairlineFigure:
    """Shares of a whole as 100 cells, one per percent, with each slice's name and share in a key beside the grid.
    More than seven slices fold into "Other", as on the donut. Cells round by the largest remainder, so they add up
    to 100 and a slice may take one cell more or less than its share in the key. Without `value`, every row counts
    once."""
    data, value = with_counts(data, value)
    ring = donut_rings(data, label, value, None, chart="waffle", colors=colors, order=order)[0]
    result = figure(title or f"{humanise(value)} by {joined([label])}", subtitle=subtitle, caption=caption,
                    size=size)
    result.description = donut_description(ring, None, None, current_settings().locale, "kind_waffle")
    result.draw(0, lambda box, measure, style: waffle_drawing({"ring": ring}, box, measure, style))
    return fit_height(result)
