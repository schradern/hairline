import pandas as pd
import pytest

import hairline as hl


def admissions():
    return pd.DataFrame({"diagnosis": ["Sepsis"] * 6 + ["Trauma"] * 3 + ["Pneumonia"] * 8 + ["Stroke"] * 2,
                         "sex": (["f", "m"] * 10)[:19]})


def bar_heights(figure):
    return [patch.get_height() for patch in figure.ax.patches]


def test_raw_rows_are_counted_and_sorted_by_value():
    figure = hl.bars(admissions(), "diagnosis")
    figure.figure.canvas.draw()
    assert bar_heights(figure) == [8, 6, 3, 2]
    assert [label.get_text() for label in figure.ax.get_xticklabels()] == ["Pneumonia", "Sepsis", "Trauma", "Stroke"]
    assert figure.title == "Count by diagnosis"


def test_values_are_labelled_at_the_bar_ends():
    figure = hl.bars(admissions(), "diagnosis")
    assert sorted(text.get_text() for text in figure.ax.texts) == ["2", "3", "6", "8"]


def test_groups_side_by_side_get_a_legend():
    figure = hl.bars(admissions(), "diagnosis", by="sex")
    figure.figure.canvas.draw()
    assert figure.layout_report()["legend_labels"] == ["f", "m"]
    assert len(figure.ax.patches) == 8


def test_long_labels_turn_the_bars_horizontal():
    data = pd.DataFrame({"reason": ["Respiratory failure after surgery", "Sepsis", "Sepsis"]})
    figure = hl.bars(data, "reason")
    assert [patch.get_width() for patch in figure.ax.patches] == [2, 1]


def test_stacked_shares_reach_one_hundred_percent():
    figure = hl.bars(admissions(), "diagnosis", by="sex", stacked=True, percent=True)
    tops = {}
    for patch in figure.ax.patches:
        x = round(patch.get_x(), 6)
        tops[x] = max(tops.get(x, 0), patch.get_y() + patch.get_height())
    assert all(top == pytest.approx(1) for top in tops.values())
