"""Labels that meet the edge of their room, the same rule in every chart: a label keeps one line while the chart
keeps its minimum size; otherwise it wraps into the room that size leaves, and a word wider than that room is a
HairlineLayoutError naming the room it needs. Labels taller than the panel grow the figure (fit_height with
shrink=False)."""

from __future__ import annotations

from collections.abc import Callable

from hairline.charts.labels import isotonic
from hairline.errors import HairlineLayoutError

Measure = Callable[..., float]

# Rounding slack in pt: a label exactly as wide as its room keeps one line.
TOLERANCE = 1e-6


def wrap_words(content: str, width: float, measure: Measure, role: str = "label",
               weight: int | None = None) -> list[str]:
    """Greedy word wrap at `width`; a word wider than the line stays on its own line."""
    lines, current = [], ""
    for word in content.split():
        candidate = f"{current} {word}" if current else word
        if current and measure(candidate, role, weight) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    return lines + [current]


def pair_width(lines: list[str], measure: Measure, value: float = 0.0, space: float = 0.0, role: str = "label",
               weight: int | None = None) -> float:
    """Width of a wrapped name whose value (`value` pt wide) follows the last line, or stands alone after an
    empty last line."""
    last = measure(lines[-1], role, weight) + space + value if lines[-1] else value
    return max([measure(line, role, weight) for line in lines[:-1]] + [last])


def pair_lines(content: str, room: float, measure: Measure, value: float = 0.0, space: float = 0.0,
               role: str = "label", weight: int | None = None) -> list[str]:
    """`content` in lines for `room`, a value `value` pt wide after the last: one line when it fits; otherwise
    wrapped so the value fits beside every line, or, when a word is too wide for that, wrapped at the full room
    with the value on a line of its own (an empty last line) if it does not fit after the last."""
    reserve = space + value if value else 0.0
    if measure(content, role, weight) + reserve <= room + TOLERANCE:
        return [content]
    lines = wrap_words(content, room - reserve + TOLERANCE, measure, role, weight)
    if pair_width(lines, measure, value, space, role, weight) <= room + TOLERANCE or not value:
        return lines
    lines = wrap_words(content, room + TOLERANCE, measure, role, weight)
    return lines if pair_width(lines, measure, value, space, role, weight) <= room + TOLERANCE else lines + [""]


def fit_lines(content: str, room: float, measure: Measure, chart: str, what: str, value: float = 0.0,
              space: float = 0.0, role: str = "label", weight: int | None = None) -> list[str]:
    """pair_lines(), and an error naming the room needed when a word (or the value) is wider than `room`."""
    lines = pair_lines(content, room, measure, value, space, role, weight)
    need = pair_width(lines, measure, value, space, role, weight)
    if need > room + TOLERANCE:
        widest = max(lines, key=lambda line: measure(line, role, weight))
        raise HairlineLayoutError(f"hairline: {chart}: {what} {widest or content!r} needs {need:.0f} pt, but the "
                                  f"figure leaves {max(room, 0.0):.0f} pt for it. Shorten the label or use a wider "
                                  "size")
    return lines


def widest_line(lines: list[str], measure: Measure, role: str = "label", weight: int | None = None) -> float:
    return max((measure(line, role, weight) for line in lines), default=0.0)


def spread_blocks(positions: list[float], heights: list[float], top: float, bottom: float) -> list[float]:
    """Centres of blocks `heights` tall, without overlap, as close to `positions` as possible, between `top` and
    `bottom`. Blocks that do not fit stack down from `top` (the figure then grows to hold them)."""
    order = sorted(range(len(positions)), key=lambda index: (positions[index], index))
    offsets, total = [], 0.0
    for rank, index in enumerate(order):
        if rank:
            total += (heights[order[rank - 1]] + heights[index]) / 2
        offsets.append(total)
    shifted = isotonic([positions[index] - offset for index, offset in zip(order, offsets, strict=True)])
    floor = top + heights[order[0]] / 2 if order else top
    ceiling = bottom - heights[order[-1]] / 2 - offsets[-1] if order else bottom
    shifted = [floor] * len(shifted) if ceiling < floor else [min(max(value, floor), ceiling) for value in shifted]
    result = [0.0] * len(positions)
    for rank, index in enumerate(order):
        result[index] = shifted[rank] + offsets[rank]
    return result
