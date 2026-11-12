"""A small table under the x-axis (number at risk), its values aligned to x positions of the first panel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from hairline.layout.axes_style import edge_alignment
from hairline.layout.draw import add_text
from hairline.layout.geometry import FrameLayout, load_font_metrics
from hairline.layout.legend import LegendItem, draw_swatch, swatch_width
from hairline.layout.measure import text_width
from hairline.layout.styles import role_style
from hairline.tokens import load_tokens

if TYPE_CHECKING:
    from hairline.figure import HairlineFigure


def table_lines(figure: HairlineFigure) -> int:
    spec = figure.table_spec
    return 0 if spec is None else len(spec["rows"]) + (1 if spec["heading"] else 0)


def table_keys(spec: dict | None, legend: list[LegendItem]) -> list[str]:
    """Each row's key takes the legend swatch of the series with the same label (a square if there is none)."""
    kinds = {item.label: item.kind for item in legend}
    return [] if spec is None else [kinds.get(label, "square") for label, _, _ in spec["rows"]]


def label_offset(figure: HairlineFigure) -> float:
    spacing, base = load_tokens()["spacing"], figure.settings.base_size
    widest = max((swatch_width(kind, base, spacing) for kind in figure.table_keys),
                 default=spacing["legend_swatch_square"] * base)
    return widest + spacing["legend_swatch_text"] * base


def table_label_width(figure: HairlineFigure) -> float:
    """Room left of the plot for the row labels plus half of a value centred on the plot's left edge."""
    if figure.table_spec is None:
        return 0.0
    style = role_style(figure.settings, "label")
    rows = figure.table_spec["rows"]
    # A compact row's label ("n") takes the room its full row leaves, so existing figures keep their frame.
    widest = max(text_width(label, style["family"], style["size"]) for label, _, _ in rows)
    values = max((text_width(text, style["family"], style["size"]) for _, _, items in rows for _, text in items),
                 default=0.0)
    return label_offset(figure) + widest + values / 2


def value_x(figure: HairlineFigure, value: float) -> float:
    box, (low, high) = figure.plot_boxes[0], figure.axes[0].get_xlim()
    return box.x + (value - low) / (high - low) * box.width


def text_span(figure: HairlineFigure, value: float, content: str, style: dict) -> tuple[float, float]:
    """Where a table text reaches: centred at its x, or aligned inward at the plot's edges, as it is drawn."""
    low, high = figure.axes[0].get_xlim()
    x, width = value_x(figure, value), text_width(content, style["family"], style["size"])
    align = edge_alignment((value - low) / (high - low))
    start = x if align == "left" else x - width if align == "right" else x - width / 2
    return start, start + width


def table_collision(figure: HairlineFigure, values: list[tuple[float, str]], style: dict) -> str | None:
    """Where neighbouring texts of a row come closer than the gap of x-axis labels (`ticks.label_rows_gap`): the
    figure's message saying what would fit; None when they stand apart."""
    gap = load_tokens()["ticks"]["label_rows_gap"] * style["size"]
    placed = sorted((*text_span(figure, value, content, style), content) for value, content in values)
    for (_, right, content), (left, _, next_content) in zip(placed, placed[1:], strict=False):
        if left - right < gap:
            return (f"hairline: the numbers under the x axis do not fit side by side: '{content}' and "
                    f"'{next_content}' leave {left - right:.1f} pt between them, and need {gap:.1f} pt. Show fewer "
                    f"stats or groups, use a wider size, or a chart that lists the numbers in a column, such as "
                    f"spread()")
    return None


def fitted_rows(figure: HairlineFigure, style: dict) -> list[tuple]:
    """Each row as drawn: in full, or in its compact form when the full texts would meet; a row that fits in
    neither stops the figure."""
    from hairline.errors import HairlineLayoutError
    spec, rows = figure.table_spec, []
    for (label, color, values), compact in zip(spec["rows"], spec.get("compact") or [None] * len(spec["rows"]),
                                               strict=True):
        problem = table_collision(figure, values, style)
        if problem and compact:
            label, values = compact
            problem = table_collision(figure, values, style)
        if problem:
            raise HairlineLayoutError(problem)
        rows.append((label, color, values))
    return rows


def draw_table(figure: HairlineFigure, layout: FrameLayout, lines: dict) -> list:
    spec = figure.table_spec
    if spec is None:
        return []
    settings, baselines = figure.settings, list(layout.table_baselines)
    label, ink = role_style(settings, "label"), role_style(settings, "label", color=settings.neutral["ink"])
    artists = [add_text(figure.figure, layout.left, baselines.pop(0), spec["heading"], label)] if spec["heading"] \
        else []
    spacing, cap = load_tokens()["spacing"], load_font_metrics().cap_height * label["size"]
    keys = figure.table_keys or ["square"] * len(spec["rows"])
    figure.table_value_xs = []
    for (name, color, values), baseline, kind in zip(fitted_rows(figure, ink), baselines, keys, strict=True):
        if color is not None:
            artists += draw_swatch(figure.figure, LegendItem(kind, color, name), layout.left, baseline - cap / 2,
                                   settings.base_size, spacing, lines)
        artists.append(add_text(figure.figure, layout.left + label_offset(figure), baseline, name, label))
        for value, content in values:
            figure.table_value_xs.append(value_x(figure, value))
            low, high = figure.axes[0].get_xlim()
            artists.append(add_text(figure.figure, figure.table_value_xs[-1], baseline, content, ink,
                                    edge_alignment((value - low) / (high - low))))
    return artists
