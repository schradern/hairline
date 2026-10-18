import matplotlib.colors as mcolors
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


def outcomes():
    return pd.DataFrame({"unit": ["Medical"] * 5 + ["Surgical"] * 4 + ["Neuro"] * 3,
                         "outcome": ["Home", "Home", "Home", "Ward", "Died", "Home", "Home", "Ward", "Ward",
                                     "Home", "Ward", "Died"]})


def test_stacked_segments_carry_their_values_and_bars_their_totals():
    figure = hl.bars(outcomes(), "unit", by="outcome", stacked=True, sort="given")
    texts = [text.get_text() for text in figure.ax.texts]
    assert texts.count("5") == 1 and texts.count("4") == 1 and texts.count("3") == 2
    inside = [text for text in figure.ax.texts if text.get_gid() == "hairline-segment"]
    assert {text.get_text() for text in inside} >= {"3", "2"}


def test_stacked_shares_label_percentages_and_skip_totals():
    figure = hl.bars(outcomes(), "unit", by="outcome", stacked=True, percent=True, horizontal=True)
    texts = [text.get_text() for text in figure.ax.texts]
    assert "60%" in texts and not any(text.get_gid() == "hairline-total" for text in figure.ax.texts)


def test_stacked_segments_are_separated_by_surface_gaps():
    figure = hl.bars(outcomes(), "unit", by="outcome", stacked=True)
    edges = {mcolors.to_hex(patch.get_edgecolor()) for patch in figure.ax.patches}
    assert edges == {figure.settings.neutral["surface"]}


def test_grouped_bars_name_both_columns_in_the_default_title():
    data = pd.DataFrame({"unit": ["A", "A", "B"], "sex": ["Female", "Male", "Female"]})
    assert hl.bars(data, "unit", by="sex").title == "Count by unit and sex"
