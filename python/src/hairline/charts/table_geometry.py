"""Table geometry in pt: a header row over hairline rules, body rows on a fixed pitch, text columns left-aligned and
numbers right-aligned, the first column wrapped when the table is wider than the figure. Pure: the same spec gives
the same shapes in both languages."""

from __future__ import annotations

from hairline.charts.donut_geometry import Measure, baseline_for, line_height, text
from hairline.charts.wrapping import TOLERANCE, wrap_words
from hairline.errors import HairlineLayoutError
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens

INDENT = "  "


def indent_of(content: str) -> tuple[int, str]:
    """Leading pairs of spaces as indent levels ('  Female' under 'Sex, n (%)'), and the text without them."""
    stripped = content.lstrip(" ")
    return (len(content) - len(stripped)) // len(INDENT), stripped


def cell_width(content: str, measure: Measure, weight: int | None, step: float) -> float:
    level, stripped = indent_of(content)
    return level * step + measure(stripped, "label", weight)


def widest(cells: list[str], measure: Measure, weight: int | None, step: float) -> float:
    return max((cell_width(content, measure, weight, step) for content in cells), default=0.0)


def widest_word(content: str, measure: Measure, weight: int | None) -> float:
    return max((measure(part, "label", weight) for part in content.split()), default=0.0)


def fitted_widths(spec: dict, box: Box, measure: Measure, style: dict) -> list[float]:
    """Each column as wide as its widest cell and heading. A table wider than the box first wraps its headings
    (down to their longest word; those that need least take back the room left first), then its first column, down to
    `table.min_column` x the base size; beyond that it is an error."""
    rules, base = load_tokens()["table"], style["base"]
    heading_weight, gap = rules["header_weight"], rules["column_gap"] * base
    columns = range(len(spec["header"]))
    body = [widest([row[index] for row in spec["rows"]], measure, None, base) for index in columns]
    headings = [cell_width(spec["header"][index], measure, heading_weight, base) for index in columns]
    natural = [max(cells, heading) for cells, heading in zip(body, headings, strict=True)]
    room = box.width - gap * (len(natural) - 1)
    if sum(natural) <= room + TOLERANCE:
        return natural
    widths = [max(cells, widest_word(spec["header"][index], measure, heading_weight))
              for index, cells in enumerate(body)]
    spare = room - sum(widths)
    # The headings that need least take back their room first, so as few as possible wrap.
    for index in sorted(columns, key=lambda column: (natural[column] - widths[column], column)):
        if spare <= 0:
            break
        grow = min(spare, natural[index] - widths[index])
        widths[index] += grow
        spare -= grow
    if spare >= -TOLERANCE:
        return widths
    first = widths[0] + spare
    if first < rules["min_column"] * base:
        raise HairlineLayoutError(f"hairline: table: the columns need {sum(widths) + gap * (len(widths) - 1):.0f} "
                                  f"pt even with wrapped headings, but the figure leaves {box.width:.0f} pt and the "
                                  f"first column cannot wrap narrower than {rules['min_column'] * base:.0f} pt. Use "
                                  f"a wider size, fewer columns or shorter headings")
    return [first, *widths[1:]]


def cell_lines(content: str, width: float, measure: Measure, weight: int | None, step: float) -> tuple[int, list[str]]:
    level, stripped = indent_of(content)
    if cell_width(content, measure, weight, step) <= width + TOLERANCE:
        return level, [stripped]
    return level, wrap_words(stripped, width - level * step + TOLERANCE, measure, "label", weight)


def column_lefts(widths: list[float], left: float, gap: float) -> list[float]:
    lefts, x = [], left
    for width in widths:
        lefts.append(x)
        x += width + gap
    return lefts


def anchor(align: str, left: float, width: float) -> float:
    return {"left": left, "right": left + width, "center": left + width / 2}[align]


def row_shapes(cells: list[str], top: float, lefts: list[float], widths: list[float], spec: dict, measure: Measure,
               style: dict, weight: int | None, bottom: bool = False) -> tuple[list[dict], float]:
    """One row's texts, each cell's lines from its top (with `bottom`, a heading row, on its last line); returns
    the shapes and the row's height."""
    rules, lead, ink = load_tokens()["table"], line_height(style, "label"), style["neutral"]["ink"]
    pitch, shapes = rules["row_pitch"] * lead, []
    wrapped = [cell_lines(content, width, measure, weight, style["base"])
               for content, width in zip(cells, widths, strict=True)]
    tallest = max(len(lines) for _, lines in wrapped)
    for index, ((level, lines), left, width) in enumerate(zip(wrapped, lefts, widths, strict=True)):
        align, shift = spec["align"][index], (tallest - len(lines)) * lead if bottom else 0.0
        for number, line in enumerate(lines):
            baseline = baseline_for(top + pitch / 2 + number * lead + shift, style, "label")
            x = anchor(align, left + (level * style["base"] if align == "left" else 0.0), width)
            shapes.append({**text(x, baseline, line, "label", ink, align, weight), "part": "cell"})
    return shapes, pitch + (tallest - 1) * lead


def rule(left: float, right: float, y: float, style: dict) -> dict:
    return {"kind": "line", "points": [[left, y], [right, y]], "color": style["neutral"]["axis"],
            "width": style["axis_width"], "role": "rule"}


def table_drawing(spec: dict, box: Box, measure: Measure, style: dict) -> list[dict]:
    """Rules above the header, under it and under the last row (the three rules of a journal table); bold rows in
    the key weight."""
    rules = load_tokens()["table"]
    widths = fitted_widths(spec, box, measure, style)
    lefts = column_lefts(widths, box.x, rules["column_gap"] * style["base"])
    right = lefts[-1] + widths[-1]
    shapes, y = [rule(box.x, right, box.y, style)], box.y
    header, height = row_shapes(spec["header"], y, lefts, widths, spec, measure, style, rules["header_weight"], True)
    shapes += header
    y += height
    shapes.append(rule(box.x, right, y, style))
    for index, cells in enumerate(spec["rows"]):
        weight = rules["header_weight"] if index in spec["bold"] else None
        row, height = row_shapes(cells, y, lefts, widths, spec, measure, style, weight)
        shapes += row
        y += height
    return shapes + [rule(box.x, right, y, style)]
