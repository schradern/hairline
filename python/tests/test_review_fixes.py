
import numpy as np
import pytest
from PIL import Image

import hairline as hl


def framed():
    figure = hl.figure("Title stays", subtitle="Subtitle stays", caption="Caption stays")
    figure.ax.plot([0, 1], [0, 1], label="Series")
    figure.legend()
    return figure


def test_tight_bbox_keeps_size_and_frame(tmp_path):
    figure = framed()
    figure.figure.savefig(tmp_path / "normal.png", dpi=72)
    report = figure.layout_report()
    figure.figure.savefig(tmp_path / "tight.png", dpi=72, bbox_inches="tight")
    with Image.open(tmp_path / "normal.png") as normal, Image.open(tmp_path / "tight.png") as tight:
        assert tight.size == normal.size
    assert figure.layout_report() == report


def test_ninth_labelled_series_is_refused():
    figure = hl.figure("T")
    for index in range(9):
        figure.ax.plot([0, 1], [index, index + 1], label=f"group {index}")
    figure.legend()
    with pytest.raises(hl.HairlineLayoutError, match="palette 'daylight' has 8 slots but 9 categories"):
        figure.figure.canvas.draw()


def test_zoom_after_first_draw_is_kept():
    figure = hl.figure("T")
    figure.ax.plot(np.arange(11), np.arange(11))
    figure.figure.canvas.draw()
    figure.ax.set_xlim(2, 3)
    figure.figure.canvas.draw()
    assert figure.ax.get_xlim() == (2, 3)


def test_too_small_figure_raises_instead_of_drawing_broken():
    figure = hl.figure("T", width_mm=60, height_mm=20, panels=3)
    with pytest.raises(hl.HairlineLayoutError, match="too small"):
        figure.figure.canvas.draw()


def test_save_strips_known_extension(tmp_path):
    paths = hl.save(framed(), tmp_path / "fig.pdf", formats=["pdf"])
    assert [path.name for path in paths] == ["fig.pdf"]


def test_failed_format_leaves_no_partial_file(tmp_path, monkeypatch):
    import hairline.export as export
    original = export.write_one

    def failing(fig, path, name, dpi, options):
        if name == "svg":
            path.write_text("partial")
            raise OSError("disk full")
        original(fig, path, name, dpi, options)
    monkeypatch.setattr(export, "write_one", failing)
    with pytest.raises(RuntimeError, match="disk full"):
        hl.save(framed(), tmp_path / "fig", formats=["png", "svg"], dpi=72)
    assert list(tmp_path.iterdir()) == []


def test_compose_columns_leave_room_for_their_own_y_labels():
    figure = hl.figure("T", size="double", panels=4, layout="compose", columns=2)
    for index, ax in enumerate(figure.axes):
        ax.plot([0, 1], [0, 10 ** (index + 2)])
    figure.figure.canvas.draw()
    report = figure.layout_report()
    first, second = report["panels"][0], report["panels"][1]
    labels = [label for label in figure.axes[1].get_yticklabels() if label.get_visible()]
    widest = max(label.get_window_extent().width for label in labels) * 72 / figure.figure.dpi
    assert second[0] - (first[0] + first[2]) >= 2 * 9 + widest - 0.5


def test_grid_rows_with_x_labels_reserve_the_band():
    figure = hl.figure("T", size="double", panels=5, layout="grid", columns=3)
    for ax in figure.axes:
        ax.plot([0, 1], [0, 1])
    figure.figure.canvas.draw()
    report = figure.layout_report()
    upper, lower = report["panels"][2], report["panels"][3]
    label = hl.load_tokens()["type"]["roles"]["label"]["factor"] * 9
    assert lower[1] - (upper[1] + upper[3]) >= 2.25 * 9 + 1.6 * label - 0.5
