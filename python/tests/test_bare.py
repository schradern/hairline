import pytest

import hairline as hl


def drawn_report(figure):
    figure.figure.canvas.draw()
    return figure.layout_report()


def test_bare_panel_has_no_ticks_or_grid():
    figure = hl.figure("T")
    figure.ax.plot([0, 1], [0, 1])
    figure.bare(0)
    drawn_report(figure)
    assert not figure.ax.axison


def test_bare_panel_reserves_no_tick_label_space():
    regular = hl.figure("T")
    regular.ax.plot([0, 1], [0, 1])
    bare = hl.figure("T")
    bare.ax.plot([0, 1], [0, 1])
    bare.bare(0)
    with_axes, without_axes = drawn_report(regular), drawn_report(bare)
    assert without_axes["panels"][0][0] == pytest.approx(without_axes["left"])
    assert without_axes["panels"][0][3] > with_axes["panels"][0][3]
    assert without_axes["bare_panels"] == [0]


def test_fixed_aspect_panel_is_centred():
    figure = hl.figure("T")
    figure.ax.plot([0, 1], [0, 1])
    figure.bare(0, aspect=1)
    report = drawn_report(figure)
    x, y, width, height = report["plot_boxes"][0]
    panel = report["panels"][0]
    assert width == pytest.approx(height, abs=0.5)
    assert x + width / 2 == pytest.approx(panel[0] + panel[2] / 2, abs=0.5)
    assert y == pytest.approx(panel[1], abs=0.5)


def test_unknown_bare_panel_is_named():
    figure = hl.figure("T")
    with pytest.raises(IndexError, match="panel 3 does not exist"):
        figure.bare(3)
