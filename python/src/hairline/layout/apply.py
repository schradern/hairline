"""apply_frame(): measure, compute the frame, then position axes and draw frame text."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from hairline.errors import HairlineLayoutError
from hairline.focus import apply_entity_colors, apply_highlight, focus_legend_items, place_reference_labels
from hairline.layout.axes_style import configure_ticks, data_interval, label_width, set_tick_visibility
from hairline.layout.bare import fitted_box
from hairline.layout.draw import add_text
from hairline.layout.frame import compute_frame
from hairline.layout.geometry import FrameInput, FrameLayout, load_font_metrics
from hairline.layout.legend import draw_legend, items_from_axes, pack_rows
from hairline.layout.measure import text_width, wrap
from hairline.layout.panels import ComposedHeader, compose_header
from hairline.layout.styles import header_gaps, header_styles, role_style
from hairline.marks import apply_light_slots
from hairline.settings import role_size
from hairline.tokens import load_tokens

if TYPE_CHECKING:
    from hairline.figure import HairlineFigure


@dataclass
class Measured:
    title: list[str]
    subtitle: list[str]
    caption: list[str]
    legend: list
    y_label_width: float
    column_label_widths: tuple[float, ...] = ()
    x_tick_rows: tuple[bool, ...] = ()


def grid_position(figure: HairlineFigure, index: int) -> tuple[int, int]:
    return divmod(index, figure.columns)


def shows_x_labels(figure: HairlineFigure, index: int) -> bool:
    if index in figure.bare_panels:
        return False
    return not figure.sharex or index + figure.columns >= len(figure.axes)


def shows_y_labels(figure: HairlineFigure, index: int) -> bool:
    if index in figure.bare_panels:
        return False
    return not figure.sharey or grid_position(figure, index)[1] == 0


def tick_target(figure: HairlineFigure, which: str) -> int:
    """Target tick count from the panel grid: 5 for one row (column), 4 for two, 3 for more (same rule in R)."""
    count = figure.columns if which == "x" else math.ceil(len(figure.axes) / figure.columns)
    return {1: 5, 2: 4}.get(count, 3)


def current_limits(ax, which: str) -> tuple[float, float]:
    return tuple(ax.get_ylim() if which == "y" else ax.get_xlim())


def tick_interval(figure: HairlineFigure, index: int, which: str) -> tuple[float, float] | None:
    """Data range for automatic limits, or None once the user (or a zoom) has set the limits."""
    ax, key = figure.axes[index], (index, which)
    if key not in figure.auto_limits:
        figure.auto_limits[key] = ax.get_autoscaley_on() if which == "y" else ax.get_autoscalex_on()
    applied = figure.applied_limits.get(key)
    if applied is not None and not all(math.isclose(a, b) for a, b in zip(applied, current_limits(ax, which),
                                                                          strict=True)):
        figure.auto_limits[key] = False
    if not figure.auto_limits[key]:
        return None
    shared = figure.sharey if which == "y" else figure.sharex
    return data_interval(figure.axes if shared else [ax], which)


def configure_all_ticks(figure: HairlineFigure) -> list[list[str]]:
    labels = []
    for index, ax in enumerate(figure.axes):
        if index in figure.bare_panels:
            labels.append([])
            continue
        for which in ("y", "x"):
            percent = which == "y" and index in figure.percent_axes
            result = configure_ticks(ax, which, tick_interval(figure, index, which), percent,
                                     figure.settings.locale, tick_target(figure, which))
            figure.applied_limits[(index, which)] = current_limits(ax, which)
            if which == "y":
                labels.append(result)
    return labels


def measure_texts(figure: HairlineFigure, width_pt: float, y_labels: list[list[str]]) -> Measured:
    settings, margin = figure.settings, load_tokens()["spacing"]["margin"] * figure.settings.base_size
    usable = width_pt - 2 * margin

    def wrapped(text: str | None, role: str) -> list[str]:
        style = role_style(settings, role)
        return wrap(text, style["family"], style["size"], style["weight"], usable) if text else []
    widths = column_widths(figure, y_labels)
    legend = figure.legend_items if figure.legend_items is not None else (
        focus_legend_items(figure, items_from_axes(figure.axes)) + figure.extra_legend_items
        if figure.collect_legend else [])
    return Measured(wrapped(figure.title, "title"), wrapped(figure.subtitle, "subtitle"),
                    wrapped(figure.caption, "caption"), legend, widths[0], tuple(widths), x_tick_rows(figure))


def column_widths(figure: HairlineFigure, y_labels: list[list[str]]) -> list[float]:
    """Widest y tick label per column, counting only panels that show their labels."""
    size, widths = role_size(figure.settings, "label"), [0.0] * figure.columns
    for index, labels in enumerate(y_labels):
        if shows_y_labels(figure, index):
            column = grid_position(figure, index)[1]
            widths[column] = max(widths[column], label_width(labels, figure.settings.font, size))
    return widths


def x_tick_rows(figure: HairlineFigure) -> tuple[bool, ...]:
    rows = math.ceil(len(figure.axes) / figure.columns)
    showing = {grid_position(figure, index)[0] for index in range(len(figure.axes)) if shows_x_labels(figure, index)}
    return tuple(row in showing for row in range(rows))


def first_column_has_axes(figure: HairlineFigure) -> bool:
    return any(index not in figure.bare_panels for index in range(0, len(figure.axes), figure.columns))


def frame_input(figure: HairlineFigure, measured: Measured, size: tuple[float, float], legend_rows: int,
                header_lines: tuple[int, ...]) -> FrameInput:
    settings = figure.settings
    sizes = {role: role_size(settings, role) for role in load_tokens()["type"]["roles"]}
    rows = math.ceil(len(figure.axes) / figure.columns)
    return FrameInput(width_pt=size[0], height_pt=size[1], base_size=settings.base_size, sizes=sizes,
                      title_lines=max(len(measured.title), 1), subtitle_lines=len(measured.subtitle),
                      legend_rows=legend_rows, caption_lines=len(measured.caption), panel_rows=rows,
                      panel_columns=figure.columns, panel_header_lines=header_lines,
                      y_title=figure.y_title_text is not None, x_title=figure.x_title_text is not None,
                      x_tick_labels=measured.x_tick_rows[-1], y_labels=first_column_has_axes(figure),
                      y_label_width_pt=measured.y_label_width,
                      column_label_widths=measured.column_label_widths, x_tick_rows=measured.x_tick_rows)


def header_bounds(layout: FrameLayout, figure: HairlineFigure, index: int) -> tuple[float, float]:
    box = layout.panels[index]
    left = layout.left if grid_position(figure, index)[1] == 0 else box.x
    return left, box.x + box.width


def compose_headers(figure: HairlineFigure, layout: FrameLayout) -> dict[int, ComposedHeader]:
    styles, gaps, composed = header_styles(figure.settings), header_gaps(figure.settings), {}
    for index, header in figure.headers.items():
        letter = chr(ord("A") + index) if figure.panel_letters else None
        left, right = header_bounds(layout, figure, index)
        composed[index] = compose_header(header, left, right, letter, styles, gaps)
    return composed


def lines_per_row(figure: HairlineFigure, composed: dict[int, ComposedHeader]) -> tuple[int, ...]:
    rows = math.ceil(len(figure.axes) / figure.columns)
    counts = [0] * rows
    for index, header in composed.items():
        row = grid_position(figure, index)[0]
        counts[row] = max(counts[row], header.lines)
    return tuple(counts)


def legend_style(figure: HairlineFigure) -> dict:
    return {**role_style(figure.settings, "label"), "base": figure.settings.base_size,
            "cap_height": load_font_metrics().cap_height}


def plan_layout(figure: HairlineFigure, measured: Measured, size: tuple[float, float]):
    spacing, margin = load_tokens()["spacing"], load_tokens()["spacing"]["margin"] * figure.settings.base_size
    placed = pack_rows(measured.legend, margin, size[0] - margin, legend_style(figure), spacing)
    legend_rows = max((entry.row for entry in placed), default=-1) + 1
    metrics = load_font_metrics()
    provisional = tuple(1 if any(grid_position(figure, i)[0] == row for i in figure.headers) else 0
                        for row in range(math.ceil(len(figure.axes) / figure.columns)))
    layout = compute_frame(frame_input(figure, measured, size, legend_rows, provisional), metrics)
    composed = compose_headers(figure, layout)
    layout = compute_frame(frame_input(figure, measured, size, legend_rows, lines_per_row(figure, composed)), metrics)
    return layout, placed, compose_headers(figure, layout)


def position_axes(figure: HairlineFigure, layout: FrameLayout, size: tuple[float, float]) -> None:
    settings = figure.settings
    y_pad = load_tokens()["spacing"]["y_labels_plot"] * settings.base_size
    x_pad = load_tokens()["spacing"]["x_tick_pad"] * role_size(settings, "label")
    figure.plot_boxes = []
    for index, ax in enumerate(figure.axes):
        box = fitted_box(layout.panels[index], figure.bare_panels.get(index))
        figure.plot_boxes.append(box)
        ax.set_position((box.x / size[0], 1 - (box.y + box.height) / size[1], box.width / size[0],
                         box.height / size[1]))
        if index in figure.bare_panels:
            ax.set_axis_off()
        else:
            set_tick_visibility(ax, shows_x_labels(figure, index), shows_y_labels(figure, index), y_pad, x_pad)


def draw_lines(figure: HairlineFigure, x: float, baselines: list[float], lines: list[str], role: str) -> list:
    style = role_style(figure.settings, role)
    return [add_text(figure.figure, x, baseline, line, style) for baseline, line in zip(baselines, lines,
                                                                                         strict=True)]


def draw_headers(figure: HairlineFigure, layout: FrameLayout, composed: dict[int, ComposedHeader]) -> list:
    artists = []
    for index, header in composed.items():
        baselines = layout.panel_header_baselines[grid_position(figure, index)[0]]
        artists += [add_text(figure.figure, run.x, baselines[run.line], run.text, run.style) for run in header.runs]
    return artists


def draw_axis_titles(figure: HairlineFigure, layout: FrameLayout) -> list:
    artists, style = [], role_style(figure.settings, "label")
    if figure.y_title_text is not None:
        artists.append(add_text(figure.figure, layout.y_title_left, layout.y_title_baseline, figure.y_title_text,
                                style))
    if figure.x_title_text is not None:
        right = max(box.x + box.width for box in layout.panels[:len(figure.axes)])
        artists.append(add_text(figure.figure, right, layout.x_title_baseline, figure.x_title_text, style, "right"))
    return artists


def draw_frame(figure: HairlineFigure, layout: FrameLayout, measured: Measured, placed, composed) -> None:
    spacing, lines = load_tokens()["spacing"], load_tokens()["lines"]
    artists = draw_lines(figure, layout.left, layout.title_baselines, measured.title, "title")
    artists += draw_lines(figure, layout.left, layout.subtitle_baselines, measured.subtitle, "subtitle")
    artists += draw_lines(figure, layout.left, layout.caption_baselines, measured.caption, "caption")
    artists += draw_legend(figure.figure, placed, layout.legend_row_centers, legend_style(figure), spacing, lines)
    artists += draw_headers(figure, layout, composed) + draw_axis_titles(figure, layout)
    figure.frame_artist.replace_children(artists)


def build_report(figure: HairlineFigure, layout: FrameLayout, measured: Measured, placed, composed) -> dict:
    data = layout.to_dict()
    data["panels"] = data["panels"][:len(figure.axes)]
    title_style = role_style(figure.settings, "title")
    data["title_line_rights"] = [layout.left + text_width(line, title_style["family"], title_style["size"],
                                                          title_style["weight"]) for line in measured.title]
    data["legend_item_rights"] = [entry.right for entry in placed]
    data["legend_labels"] = [entry.item.label for entry in placed]
    data["panel_header_lines"] = [composed[index].lines if index in composed else 0
                                  for index in range(len(figure.axes))]
    data["bare_panels"] = sorted(figure.bare_panels)
    data["plot_boxes"] = [[box.x, box.y, box.width, box.height] for box in figure.plot_boxes]
    data["panel_letters"] = [chr(ord("A") + index) for index in sorted(composed)] if figure.panel_letters else []
    return round_report(data)


def round_report(value):
    if isinstance(value, float):
        return round(value, 2)
    if isinstance(value, list):
        return [round_report(item) for item in value]
    if isinstance(value, dict):
        return {key: round_report(item) for key, item in value.items()}
    return value


def check_categories(figure: HairlineFigure) -> None:
    """Refuse more labelled series than palette slots instead of letting matplotlib repeat colours."""
    count, slots = len(items_from_axes(figure.axes)), len(figure.settings.palette)
    if count > slots:
        raise HairlineLayoutError(f"hairline: {figure.settings.palette_label} has {slots} slots but {count} categories "
                                  "were given; fold small categories into 'Other' or split the figure into panels")


def apply_frame(figure: HairlineFigure) -> dict[int, list[str]]:
    """Lay out the figure; return key-number labels dropped per panel."""
    check_categories(figure)
    size = tuple(value * 72 for value in figure.figure.get_size_inches())
    apply_entity_colors(figure)
    apply_highlight(figure)
    apply_light_slots(figure.axes, figure.settings, figure.light_slot_done, figure.point_done)
    measured = measure_texts(figure, size[0], configure_all_ticks(figure))
    layout, placed, composed = plan_layout(figure, measured, size)
    position_axes(figure, layout, size)
    place_reference_labels(figure)
    draw_frame(figure, layout, measured, placed, composed)
    figure.report = build_report(figure, layout, measured, placed, composed)
    return {index: header.dropped for index, header in composed.items() if header.dropped}
