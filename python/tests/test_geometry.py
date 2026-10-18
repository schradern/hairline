import json
from dataclasses import replace

import pytest

from hairline.errors import HairlineLayoutError
from hairline.layout.frame import compute_frame
from hairline.layout.geometry import FrameInput, frame_input_from_dict, load_font_metrics

BASE = 9.0
SIZES = {"title": 13.5, "subtitle": 9.0, "panel": 9.0, "label": 8.1, "caption": 7.65}
METRICS = load_font_metrics()


def line_height(size: float) -> float:
    return size * (METRICS.cap_height + METRICS.descender)


def single_panel_spec(**changes) -> FrameInput:
    spec = FrameInput(width_pt=482, height_pt=361, base_size=BASE, sizes=SIZES, title_lines=1, subtitle_lines=1,
                      legend_rows=1, caption_lines=1, panel_rows=1, panel_columns=1, panel_header_lines=(),
                      y_title=False, x_title=False, x_tick_labels=True, y_label_width_pt=20)
    return replace(spec, **changes)


def test_margin_and_left_edge():
    layout = compute_frame(single_panel_spec(), METRICS)
    assert layout.title_baselines[0] - 13.5 * METRICS.cap_height == pytest.approx(1.75 * BASE)
    assert layout.left == pytest.approx(1.75 * BASE) and layout.right == pytest.approx(482 - 1.75 * BASE)
    assert layout.panels[0].x == pytest.approx(1.75 * BASE + 20 + 0.5 * BASE)


def test_title_subtitle_gap_is_edge_to_edge():
    layout = compute_frame(single_panel_spec(), METRICS)
    subtitle_top = layout.subtitle_baselines[0] - 9.0 * METRICS.cap_height
    title_bottom = layout.title_baselines[0] + 13.5 * METRICS.descender
    assert subtitle_top - title_bottom == pytest.approx(0.35 * BASE)


def test_without_subtitle_nothing_shifts_by_hand():
    with_subtitle = compute_frame(single_panel_spec(), METRICS)
    without = compute_frame(single_panel_spec(subtitle_lines=0), METRICS)
    shift = with_subtitle.legend_row_centers[0] - without.legend_row_centers[0]
    assert shift == pytest.approx(0.35 * BASE + line_height(9.0))


def test_legend_to_content_gap():
    layout = compute_frame(single_panel_spec(), METRICS)
    legend_bottom = layout.legend_row_centers[0] + line_height(8.1) / 2
    assert layout.panels[0].y - legend_bottom == pytest.approx(1.5 * BASE)


def test_rows_layout_gaps():
    layout = compute_frame(single_panel_spec(panel_rows=4, panel_header_lines=(1, 1, 1, 1)), METRICS)
    for upper, lower in zip(layout.panels, layout.panels[1:], strict=False):
        header_top = lower.y - 0.6 * BASE - line_height(9.0)
        assert header_top - (upper.y + upper.height) == pytest.approx(2.25 * BASE)
    heights = {round(panel.height, 6) for panel in layout.panels}
    assert len(heights) == 1


def test_grid_columns_gap():
    layout = compute_frame(single_panel_spec(panel_rows=2, panel_columns=3), METRICS)
    first, second = layout.panels[0], layout.panels[1]
    assert second.x - (first.x + first.width) == pytest.approx(2.0 * BASE)
    assert layout.panels[2].x + layout.panels[2].width == pytest.approx(layout.right)


def test_caption_sits_at_bottom_margin():
    layout = compute_frame(single_panel_spec(), METRICS)
    assert layout.caption_baselines[-1] + 7.65 * METRICS.descender == pytest.approx(361 - 1.75 * BASE)


def test_long_title_two_lines_pushes_content_down():
    one = compute_frame(single_panel_spec(), METRICS)
    two = compute_frame(single_panel_spec(title_lines=2), METRICS)
    assert len(two.title_baselines) == 2 and two.panels[0].y > one.panels[0].y
    assert two.title_baselines[1] - two.title_baselines[0] == pytest.approx(line_height(13.5) + 0.25 * 13.5)


def test_y_title_above_plot():
    layout = compute_frame(single_panel_spec(y_title=True), METRICS)
    assert layout.y_title_left == pytest.approx(1.75 * BASE)
    gap = layout.panels[0].y - (layout.y_title_baseline + 8.1 * METRICS.descender)
    assert gap == pytest.approx(0.85 * BASE)


def test_too_small_figure_is_reported():
    with pytest.raises(HairlineLayoutError, match="too small.*4 panel rows"):
        compute_frame(single_panel_spec(height_pt=120, panel_rows=4), METRICS)


def flatten(value) -> list[float]:
    if isinstance(value, (list, tuple)):
        return [number for item in value for number in flatten(item)]
    return [] if value is None else [value]


def test_fixture_cases(repo_root):
    for case in json.loads((repo_root / "tokens/fixtures/frame.json").read_text()):
        actual = compute_frame(frame_input_from_dict(case["input"]), METRICS).to_dict()
        for key, value in case["layout"].items():
            assert flatten(actual[key]) == pytest.approx(flatten(value), abs=1e-6), key


def test_columns_with_own_y_labels_get_room():
    layout = compute_frame(single_panel_spec(panel_rows=2, panel_columns=2, column_label_widths=(0, 20)), METRICS)
    first, second = layout.panels[0], layout.panels[1]
    assert second.x - (first.x + first.width) == pytest.approx(2.0 * BASE + 20 + 0.5 * BASE)
    assert second.x + second.width == pytest.approx(layout.right)


def test_inner_rows_with_x_labels_get_the_tick_band():
    layout = compute_frame(single_panel_spec(panel_rows=2, panel_header_lines=(1, 1), x_tick_rows=(True, True)),
                           METRICS)
    upper, lower = layout.panels[0], layout.panels[1]
    header_top = lower.y - 0.6 * BASE - line_height(9.0)
    assert header_top - (upper.y + upper.height) == pytest.approx(2.25 * BASE + 1.6 * 8.1)


def test_rows_with_their_own_axis_titles_get_a_title_line():
    plain = compute_frame(single_panel_spec(panel_rows=2, panel_header_lines=(1, 1), x_tick_rows=(True, True)),
                          METRICS)
    titled = compute_frame(single_panel_spec(panel_rows=2, panel_header_lines=(1, 1), x_tick_rows=(True, True),
                                             x_title_rows=(True, True)), METRICS)
    assert titled.x_title_row_baselines[0] > titled.panels[0].y + titled.panels[0].height
    assert titled.x_title_row_baselines[1] == titled.x_title_baseline
    assert titled.panels[0].height < plain.panels[0].height
