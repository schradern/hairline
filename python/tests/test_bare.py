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


def test_table_band_sits_between_axis_and_caption():
    plain = hl.figure("T", caption="Note.")
    plain.ax.plot([0, 10], [0, 1])
    with_table = hl.figure("T", caption="Note.")
    with_table.ax.plot([0, 10], [0, 1])
    with_table.table([("Group A", "#2474cf", [(0, "40"), (5, "31"), (10, "12")]),
                      ("Group B", "#e8a628", [(0, "38"), (5, "20"), (10, "6")])], heading="Number at risk")
    first, second = drawn_report(plain), drawn_report(with_table)
    panel = second["panels"][0]
    assert len(second["table_baselines"]) == 3
    assert panel[1] + panel[3] < second["table_baselines"][0] < second["table_baselines"][-1] < \
        second["caption_baselines"][0]
    assert second["panels"][0][3] < first["panels"][0][3]


def test_table_values_align_with_their_x_position():
    figure = hl.figure("T")
    figure.ax.plot([0, 10], [0, 1])
    figure.table([("Group A", "#2474cf", [(0, "40"), (10, "12")])])
    report = drawn_report(figure)
    x, _, width, _ = report["plot_boxes"][0]
    assert [round(value, 1) for value in report["table_value_xs"]] == [round(x, 1), round(x + width, 1)]
