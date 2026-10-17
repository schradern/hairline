import warnings

import numpy as np
import pytest

import hairline as hl

STATS = [("HR", "0.58 [0.41; 0.82]"), ("Log-rank p", "0.004"), ("Median", "17.9 vs 31.2 months")]


def drawn(figure):
    figure.figure.canvas.draw()
    return figure.layout_report()


def test_figure_report_matches_geometry():
    hl.use()
    figure = hl.figure("ICU bed occupancy", subtitle="Share of beds occupied", caption="Source: test",
                       size="double", panels=4)
    for ax in figure.axes:
        ax.plot(range(10), np.linspace(0.2, 0.9, 10))
    report = drawn(figure)
    assert len(report["panels"]) == 4
    assert report["left"] == pytest.approx(1.75 * 9)
    assert len(report["title_baselines"]) == 1 and len(report["caption_baselines"]) == 1


def test_preset_base_size_applies_unless_explicit():
    assert hl.figure("T", size="single").settings.base_size == 8
    hl.use(base_size=10)
    assert hl.figure("T", size="single").settings.base_size == 10


def test_figure_size_from_preset():
    figure = hl.figure("T", size="double")
    width, height = figure.figure.get_size_inches()
    assert width == pytest.approx(174 / 25.4) and height == pytest.approx(174 * 0.6 / 25.4)


def test_panel_header_single_line_when_it_fits():
    figure = hl.figure("T", size="double")
    figure.panel_header(0, "Early vs standard", stats=STATS)
    assert drawn(figure)["panel_header_lines"] == [1]


def test_panel_header_fallback_to_second_line():
    figure = hl.figure("T", size="onehalf")
    figure.panel_header(0, "Early vs standard", stats=STATS)
    assert drawn(figure)["panel_header_lines"] == [2]


def test_panel_header_drops_with_warning_when_two_lines_overflow():
    figure = hl.figure("T", size="single")
    figure.panel_header(0, "Name", stats=[("Alpha", "1" * 20), ("Beta", "2" * 20), ("Gamma", "3" * 40)])
    with pytest.warns(UserWarning, match="dropped.*Gamma"):
        drawn(figure)


def test_legend_wraps_instead_of_overflowing():
    figure = hl.figure("T", size="single")
    figure.legend([("square", color, f"Category {index}") for index, color in enumerate(hl.palette(n=8))])
    report = drawn(figure)
    assert len(report["legend_row_centers"]) >= 2
    assert all(right <= report["right"] + 0.5 for right in report["legend_item_rights"])


def test_legend_collected_from_axes():
    figure = hl.figure("T")
    figure.ax.plot([0, 1], [0, 1], label="Standard care")
    figure.ax.plot([0, 1], [1, 0], label="Early mobilisation")
    figure.legend()
    report = drawn(figure)
    assert report["legend_labels"] == ["Standard care", "Early mobilisation"]


def test_long_title_wraps_without_clipping():
    figure = hl.figure("A very long title that keeps going " * 4, size="single")
    report = drawn(figure)
    assert len(report["title_baselines"]) >= 2
    assert max(report["title_line_rights"]) <= report["right"] + 0.5


def test_rows_layout_hides_inner_x_tick_labels():
    figure = hl.figure("T", panels=3, layout="rows")
    for ax in figure.axes:
        ax.plot(range(5), range(5))
    drawn(figure)
    for ax in figure.axes[:2]:
        assert not any(label.get_visible() for label in ax.get_xticklabels())
    assert any(label.get_visible() for label in figure.axes[2].get_xticklabels())


def test_grid_layout_columns():
    figure = hl.figure("T", size="double", panels=6, layout="grid", columns=3)
    report = drawn(figure)
    xs = sorted({round(panel[0], 3) for panel in report["panels"]})
    assert len(xs) == 3


def test_y_title_above_axis_on_left_edge():
    figure = hl.figure("T")
    figure.y_title("Days on ICU")
    report = drawn(figure)
    assert report["y_title_left"] == pytest.approx(1.75 * 9)
    assert report["y_title_baseline"] < report["panels"][0][1]


def test_y_ticks_use_nice_breaks_and_locale():
    hl.use(locale="de")
    figure = hl.figure("T")
    figure.ax.plot([0, 1, 2], [0.21, 0.5, 0.88])
    drawn(figure)
    assert list(figure.ax.get_yticks()) == pytest.approx([0, 0.25, 0.5, 0.75, 1.0])
    assert [label.get_text() for label in figure.ax.get_yticklabels()][:2] == ["0,00", "0,25"]


def test_percent_axis_marks_top_tick_only():
    figure = hl.figure("T")
    figure.ax.plot([0, 1], [0.2, 0.9])
    figure.percent_axis(0)
    drawn(figure)
    labels = [label.get_text() for label in figure.ax.get_yticklabels()]
    assert labels[-1].endswith("%") and not labels[0].endswith("%")


def test_redraw_is_idempotent():
    figure = hl.figure("Title", subtitle="Sub", caption="Cap")
    first = drawn(figure)
    assert drawn(figure) == first
    texts = [child for child in figure.frame_artist.get_children() if hasattr(child, "get_text")]
    assert len(texts) == len([*first["title_baselines"], *first["subtitle_baselines"], *first["caption_baselines"]])


def test_panel_letters():
    figure = hl.figure("T", panels=2, layout="compose", columns=2, panel_letters=True)
    figure.panel_header(0, "Survival")
    figure.panel_header(1, "Forest plot")
    assert drawn(figure)["panel_letters"] == ["A", "B"]


def test_unknown_layout_and_size_messages():
    with pytest.raises(ValueError, match="unknown layout 'mosaic'.*compose, grid, pair, rows"):
        hl.figure("T", layout="mosaic")
    with pytest.raises(ValueError, match="unknown size 'poster'.*a4, double, onehalf, single, slide"):
        hl.figure("T", size="poster")


def test_frame_on_existing_figure():
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.plot([1, 2], [3, 4])
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        framed = hl.frame(fig, "Existing figure", subtitle="framed afterwards")
    assert len(drawn(framed)["title_baselines"]) == 1


def test_frame_text_is_drawn_on_first_save(tmp_path):
    figure = hl.figure("Visible on the first draw", caption="Caption too")
    path = tmp_path / "first.svg"
    figure.figure.savefig(path)
    content = path.read_text()
    assert "Visible on the first draw" in content and "Caption too" in content


def test_shared_y_axis_covers_every_panel():
    figure = hl.figure("T", size="double", panels=3)
    for index, ax in enumerate(figure.axes):
        ax.plot([0, 1], [0.2 + index * 0.3, 0.3 + index * 0.3])
    drawn(figure)
    low, high = figure.axes[0].get_ylim()
    assert low <= 0.2 and high >= 0.9
    assert all(ax.get_ylim() == (low, high) for ax in figure.axes)


def test_short_panels_get_fewer_ticks():
    figure = hl.figure("T", size="double", panels=4)
    for ax in figure.axes:
        ax.plot([0, 1], [0.2, 0.9])
    drawn(figure)
    assert 3 <= len(figure.axes[0].get_yticks()) <= 4


@pytest.mark.parametrize("panels, expected", [(1, 5), (2, 4), (3, 3), (6, 3)])
def test_tick_target_depends_on_panel_rows_only(panels, expected):
    from hairline.layout.apply import tick_target
    for size in ("single", "slide"):
        assert tick_target(hl.figure("T", size=size, panels=panels), "y") == expected


@pytest.mark.parametrize("columns, expected", [(1, 5), (2, 4), (3, 3)])
def test_x_tick_target_depends_on_columns(columns, expected):
    from hairline.layout.apply import tick_target
    figure = hl.figure("T", size="double", panels=columns * 2, layout="grid", columns=columns)
    assert tick_target(figure, "x") == expected
