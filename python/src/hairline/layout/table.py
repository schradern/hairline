"""A small table under the x-axis (number at risk), its values aligned to x positions of the first panel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from hairline.layout.draw import add_rect, add_text
from hairline.layout.geometry import FrameLayout, load_font_metrics
from hairline.layout.measure import text_width
from hairline.layout.styles import role_style
from hairline.tokens import load_tokens

if TYPE_CHECKING:
    from hairline.figure import HairlineFigure


def table_lines(figure: HairlineFigure) -> int:
    spec = figure.table_spec
    return 0 if spec is None else len(spec["rows"]) + (1 if spec["heading"] else 0)


def label_offset(figure: HairlineFigure) -> float:
    spacing = load_tokens()["spacing"]
    return (spacing["legend_swatch_square"] + spacing["legend_swatch_text"]) * figure.settings.base_size


def table_label_width(figure: HairlineFigure) -> float:
    """Room left of the plot for the row labels plus half of a value centred on the plot's left edge."""
    if figure.table_spec is None:
        return 0.0
    style = role_style(figure.settings, "label")
    rows = figure.table_spec["rows"]
    widest = max(text_width(label, style["family"], style["size"]) for label, _, _ in rows)
    values = max((text_width(text, style["family"], style["size"]) for _, _, items in rows for _, text in items),
                 default=0.0)
    return label_offset(figure) + widest + values / 2


def value_x(figure: HairlineFigure, value: float) -> float:
    box, (low, high) = figure.plot_boxes[0], figure.axes[0].get_xlim()
    return box.x + (value - low) / (high - low) * box.width


def draw_table(figure: HairlineFigure, layout: FrameLayout) -> list:
    spec = figure.table_spec
    if spec is None:
        return []
    settings, baselines = figure.settings, list(layout.table_baselines)
    label, ink = role_style(settings, "label"), role_style(settings, "label", color=settings.neutral["ink"])
    artists = [add_text(figure.figure, layout.left, baselines.pop(0), spec["heading"], label)] if spec["heading"] \
        else []
    side = load_tokens()["spacing"]["legend_swatch_square"] * settings.base_size
    cap = load_font_metrics().cap_height * label["size"]
    figure.table_value_xs = []
    for (name, color, values), baseline in zip(spec["rows"], baselines, strict=True):
        if color is not None:
            artists.append(add_rect(figure.figure, layout.left, baseline - cap / 2 - side / 2, side, side, color))
        artists.append(add_text(figure.figure, layout.left + label_offset(figure), baseline, name, label))
        for value, content in values:
            figure.table_value_xs.append(value_x(figure, value))
            artists.append(add_text(figure.figure, figure.table_value_xs[-1], baseline, content, ink, "center"))
    return artists
