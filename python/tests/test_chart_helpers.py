import pytest

from hairline.charts.common import fold_other
from hairline.charts.labels import spread_labels
from hairline.color.space import hex_to_oklch
from hairline.color.tints import tints


def test_labels_without_overlap_stay_put():
    assert spread_labels([0, 10, 20], 5, -100, 100) == pytest.approx([0, 10, 20])


def test_overlapping_labels_move_apart_symmetrically():
    assert spread_labels([10, 10, 10], 4, -100, 100) == pytest.approx([6, 10, 14])


def test_spread_labels_keep_input_order():
    assert spread_labels([12, 0, 10], 4, -100, 100) == pytest.approx([13, 0, 9])


def test_spread_labels_stay_within_bounds():
    result = spread_labels([0, 1, 2], 4, 0, 100)
    assert result == pytest.approx([0, 4, 8])


def test_labels_that_cannot_fit_are_centred():
    assert spread_labels([0, 0, 0], 10, 0, 10) == pytest.approx([-5, 5, 15])


def test_tints_keep_hue_and_get_lighter():
    colours = tints("#2474cf", 3)
    lightness = [hex_to_oklch(colour)[0] for colour in colours]
    assert lightness == sorted(lightness) and lightness[0] > hex_to_oklch("#2474cf")[0]
    assert all(abs(hex_to_oklch(colour)[2] - hex_to_oklch("#2474cf")[2]) < 3 for colour in colours)
    assert lightness[-1] <= 0.92 + 1e-6 and len(set(colours)) == 3


def test_fold_other_keeps_order_and_sums():
    labels, values = fold_other(list("abcdefghi"), [5, 1, 9, 2, 8, 3, 7, 4, 6], keep=4)
    assert labels == ["c", "e", "g", "Other"]
    assert values == [9, 8, 7, 21]


def test_fold_other_leaves_short_lists_alone():
    assert fold_other(["a", "b"], [1, 2]) == (["a", "b"], [1, 2])


def test_tints_of_a_light_parent_step_darker():
    lightness = [hex_to_oklch(colour)[0] for colour in tints("#e8a628", 2)]
    assert lightness[0] < hex_to_oklch("#e8a628")[0] and lightness[1] < lightness[0]
