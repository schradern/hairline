"""compute_frame(): stacks header, legend, panels and caption using the spacing scale."""

from __future__ import annotations

from hairline.errors import HairlineLayoutError
from hairline.layout.geometry import Box, FontMetrics, FrameInput, FrameLayout, Stack
from hairline.tokens import load_tokens


def header_lines(spec: FrameInput, row: int) -> int:
    return spec.panel_header_lines[row] if row < len(spec.panel_header_lines) else 0


def inner_tick_band(spec: FrameInput, row: int, spacing: dict) -> float:
    """Height for x tick labels under a row that is not the last one (0 unless that row shows them)."""
    shows = row < len(spec.x_tick_rows) and spec.x_tick_rows[row] and row < spec.panel_rows - 1
    return spacing["x_tick_labels"] * spec.sizes["label"] if shows else 0.0


def column_offsets(spec: FrameInput, spacing: dict) -> list[float]:
    """Extra room before each column for its own y tick labels (column 0 uses y_label_width_pt)."""
    widths = list(spec.column_label_widths) + [0.0] * spec.panel_columns
    return [0.0] + [widths[column] + spacing["y_labels_plot"] * spec.base_size if widths[column] > 0 else 0.0
                    for column in range(1, spec.panel_columns)]


def place_header(stack: Stack, spec: FrameInput, layout: FrameLayout, spacing: dict) -> None:
    base, sizes = spec.base_size, spec.sizes
    stack.skip(spacing["margin"] * base)
    layout.title_baselines = stack.lines(sizes["title"], spec.title_lines)
    if spec.subtitle_lines:
        stack.skip(spacing["title_subtitle"] * base)
        layout.subtitle_baselines = stack.lines(sizes["subtitle"], spec.subtitle_lines)
    if spec.legend_rows:
        stack.skip(spacing["header_legend"] * base)
        layout.legend_row_centers = stack.centered_rows(sizes["label"], spec.legend_rows,
                                                        spacing["legend_rows"] * base)
    stack.skip(spacing["legend_content"] * base)


def fixed_row_height(spec: FrameInput, row: int, spacing: dict, metrics: FontMetrics, line_gap: float) -> float:
    """Height of everything in a panel row except the panel itself."""
    def text_block(size: float, count: int) -> float:
        return 0.0 if count == 0 else size * (count * (metrics.cap_height + metrics.descender) + (count - 1) * line_gap)
    base, height = spec.base_size, 0.0
    if header_lines(spec, row):
        height += text_block(spec.sizes["panel"], header_lines(spec, row)) + spacing["panel_header"] * base
    if row == 0 and spec.y_title:
        height += text_block(spec.sizes["label"], 1) + spacing["y_title"] * base
    if row:
        height += spacing["panel_rows"] * base
    return height + inner_tick_band(spec, row, spacing)


def fixed_bottom_height(spec: FrameInput, spacing: dict, metrics: FontMetrics, line_gap: float) -> float:
    base, label, caption = spec.base_size, spec.sizes["label"], spec.sizes["caption"]
    height = spacing["x_tick_labels"] * label if spec.x_tick_labels else 0.0
    if spec.x_title:
        height += spacing["x_title"] * base + label * (metrics.cap_height + metrics.descender)
    if spec.table_lines:
        lines = spec.table_lines
        height += spacing["table_gap"] * base
        height += label * (lines * (metrics.cap_height + metrics.descender) + (lines - 1) * line_gap)
    if spec.caption_lines:
        lines = spec.caption_lines
        height += spacing["content_caption"] * base
        height += caption * (lines * (metrics.cap_height + metrics.descender) + (lines - 1) * line_gap)
    return height + spacing["margin"] * base


def panel_height(spec: FrameInput, top: float, spacing: dict, metrics: FontMetrics, line_gap: float) -> float:
    fixed = sum(fixed_row_height(spec, row, spacing, metrics, line_gap) for row in range(spec.panel_rows))
    available = spec.height_pt - top - fixed - fixed_bottom_height(spec, spacing, metrics, line_gap)
    height = available / spec.panel_rows
    if height < spacing["min_panel_height"] * spec.base_size:
        raise HairlineLayoutError(f"hairline: figure too small: {spec.height_pt:.0f} pt high leaves {height:.1f} pt "
                                  f"per panel for {spec.panel_rows} panel rows; make it taller or use fewer rows")
    return height


def place_panels(stack: Stack, spec: FrameInput, layout: FrameLayout, spacing: dict, height: float) -> None:
    base = spec.base_size
    gap = spacing["panel_columns"] * base
    offsets = column_offsets(spec, spacing)
    width = (layout.right - layout.plot_left - gap * (spec.panel_columns - 1) - sum(offsets)) / spec.panel_columns
    for row in range(spec.panel_rows):
        if row:
            stack.skip(spacing["panel_rows"] * base)
        baselines = stack.lines(spec.sizes["panel"], header_lines(spec, row))
        layout.panel_header_baselines.append(baselines)
        if baselines:
            stack.skip(spacing["panel_header"] * base)
        if row == 0 and spec.y_title:
            layout.y_title_left = layout.left
            layout.y_title_baseline = stack.lines(spec.sizes["label"], 1)[0]
            stack.skip(spacing["y_title"] * base)
        layout.panels += [Box(layout.plot_left + column * (width + gap) + sum(offsets[: column + 1]), stack.y, width,
                              height) for column in range(spec.panel_columns)]
        stack.skip(height + inner_tick_band(spec, row, spacing))


def place_bottom(stack: Stack, spec: FrameInput, layout: FrameLayout, spacing: dict) -> None:
    base = spec.base_size
    if spec.x_tick_labels:
        stack.skip(spacing["x_tick_labels"] * spec.sizes["label"])
    if spec.x_title:
        stack.skip(spacing["x_title"] * base)
        layout.x_title_baseline = stack.lines(spec.sizes["label"], 1)[0]
    if spec.table_lines:
        stack.skip(spacing["table_gap"] * base)
        layout.table_baselines = stack.lines(spec.sizes["label"], spec.table_lines)
    if spec.caption_lines:
        stack.skip(spacing["content_caption"] * base)
        layout.caption_baselines = stack.lines(spec.sizes["caption"], spec.caption_lines)


def compute_frame(spec: FrameInput, metrics: FontMetrics) -> FrameLayout:
    """Place every frame element; all positions in pt from the figure's top-left corner."""
    tokens = load_tokens()
    spacing, line_gap = tokens["spacing"], tokens["type"]["line_gap"]
    left = spacing["margin"] * spec.base_size
    layout = FrameLayout(left=left, right=spec.width_pt - left,
                         plot_left=left + (spec.y_label_width_pt + spacing["y_labels_plot"] * spec.base_size
                                           if spec.y_labels else 0.0))
    stack = Stack(0.0, metrics, line_gap)
    place_header(stack, spec, layout, spacing)
    height = panel_height(spec, stack.y, spacing, metrics, line_gap)
    place_panels(stack, spec, layout, spacing, height)
    place_bottom(stack, spec, layout, spacing)
    return layout
