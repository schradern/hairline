import matplotlib.colors as mcolors
import pytest

import hairline as hl

STATS = [("Mean", "87.0%"), ("Median", "87.9%"), ("Days ≥ 90%", "42%")]


def drawn(figure):
    figure.figure.canvas.draw()
    return figure


def texts(figure):
    return {child.get_text(): child for child in figure.frame_artist.get_children() if hasattr(child, "get_text")}


def test_key_number_is_emphasised():
    figure = hl.figure("T", size="double")
    figure.panel_header(0, "Unit B", stats=STATS, key="Days ≥ 90%")
    found = texts(drawn(figure))
    settings = figure.settings
    assert mcolors.to_hex(found["42%"].get_color()) == settings.neutral["ink"] and found["42%"].get_fontweight() == 600
    assert mcolors.to_hex(found["87.0%"].get_color()) == settings.neutral["muted"]


def test_unknown_key_is_named():
    figure = hl.figure("T")
    with pytest.raises(ValueError, match="key 'Days' is not one of the key numbers: Mean, Median, Days ≥ 90%"):
        figure.panel_header(0, "Unit B", stats=STATS, key="Days")


def test_highlight_series_keeps_colour_and_greys_the_rest():
    figure = hl.figure("T")
    focus = figure.ax.plot([0, 1], [0, 1], label="Sepsis")[0]
    other = figure.ax.plot([0, 1], [1, 0], label="Trauma")[0]
    base_width = focus.get_linewidth()
    figure.highlight(series=["Sepsis"])
    drawn(figure)
    assert mcolors.to_hex(focus.get_color()) == hl.palette()[0]
    assert mcolors.to_hex(other.get_color()) == "#b3b8be"
    assert focus.get_linewidth() == pytest.approx(1.15 * base_width)
    assert other.get_linewidth() == pytest.approx(0.85 * base_width)


def test_highlight_panels_by_name_and_light_slots_skip_context():
    figure = hl.figure("T", size="double", panels=3)
    lines = [ax.plot([0, 1], [0, 1], color=hl.palette()[0])[0] for ax in figure.axes]
    for index, name in enumerate(["Unit A", "Unit B", "Unit D"]):
        figure.panel_header(index, name)
    figure.highlight(panels=["Unit B"])
    drawn(figure)
    drawn(figure)
    assert [mcolors.to_hex(line.get_color()) for line in lines] == ["#b3b8be", hl.palette()[0], "#b3b8be"]
    assert lines[0].get_linewidth() == pytest.approx(0.85 * 0.14 * 9)


def test_unknown_highlight_is_reported_at_draw():
    figure = hl.figure("T")
    figure.ax.plot([0, 1], [0, 1], label="Sepsis")
    figure.highlight(series=["Pneumonia"])
    with pytest.raises(hl.HairlineLayoutError, match="highlight: 'Pneumonia' is not a series label; labels: Sepsis"):
        figure.figure.canvas.draw()


def test_reference_line_with_label_in_every_panel():
    figure = hl.figure("T", size="double", panels=2)
    for ax in figure.axes:
        ax.plot([0, 1], [0.2, 0.85])
    figure.reference(y=0.9, label="90 %", legend_label="High-load threshold")
    figure.legend()
    drawn(figure)
    for ax in figure.axes:
        reference = [line for line in ax.lines if line.get_gid() == "hairline-reference"]
        assert len(reference) == 1 and mcolors.to_hex(reference[0].get_color()) == "#a3a8ae"
        assert [text.get_text() for text in ax.texts] == ["90 %"]
    assert figure.layout_report()["legend_labels"] == ["High-load threshold"]


def test_reference_label_stays_above_when_the_header_gap_has_room():
    figure = hl.figure("T", size="double", panels=3)
    for index, ax in enumerate(figure.axes):
        ax.plot([0, 1], [0.4, 0.8])
        figure.panel_header(index, f"Unit {index}")
    figure.reference(y=0.9, label="90 %")
    drawn(figure)
    assert all(ax.texts[0].get_va() == "bottom" for ax in figure.axes)


def test_reference_label_moves_below_when_it_would_reach_the_header():
    figure = hl.figure("T")
    figure.ax.plot([0, 1], [0, 1])
    figure.panel_header(0, "Unit")
    figure.reference(y=1.0, label="100 %")
    drawn(figure)
    assert figure.ax.texts[0].get_va() == "top"


def test_legend_shows_the_highlighted_colour():
    figure = hl.figure("T", size="double", panels=2)
    for index, ax in enumerate(figure.axes):
        ax.plot([0, 1], [0, 1], color=hl.palette()[0], label="7-day mean")
        figure.panel_header(index, f"Unit {index}")
    figure.highlight(panels=["Unit 1"])
    figure.legend()
    drawn(figure)
    swatches = [child for child in figure.frame_artist.get_children() if not hasattr(child, "get_text")]
    assert mcolors.to_hex(swatches[0].get_color()) == hl.palette()[0]
