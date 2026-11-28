import json
from pathlib import Path

import pandas as pd
import pytest
from test_donut import STYLE, discharge, fake_measure

import hairline as hl
from hairline.charts.donut import donut_rings
from hairline.charts.waffle import cell_counts, waffle_drawing
from hairline.layout.geometry import Box

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "waffle.json").read_text(encoding="utf-8"))


def cells(shapes):
    return [shape for shape in shapes if shape.get("series") is not None]


@pytest.mark.parametrize("case", FIXTURE["counts"], ids=lambda case: str(case["shares"]))
def test_cells_match_the_shared_fixture(case):
    assert cell_counts(case["shares"], 100) == case["cells"]


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda case: str(case["box"]))
def test_drawing_matches_the_shared_fixture(case):
    shapes = waffle_drawing(case["spec"], Box(*case["box"]), fake_measure, FIXTURE["style"])
    assert [shape["kind"] for shape in shapes] == [shape["kind"] for shape in case["shapes"]]
    for drawn, expected in zip(shapes, case["shapes"], strict=True):
        if drawn["kind"] == "text":
            assert drawn["text"] == expected["text"]
            assert (drawn["x"], drawn["y"]) == pytest.approx((expected["x"], expected["y"]))
        else:
            assert [value for point in drawn["points"] for value in point] == pytest.approx(
                [value for point in expected["points"] for value in point])


def test_cells_always_add_up_to_a_hundred():
    for shares in ([0.004, 0.996], [1 / 7] * 7, [0.5049, 0.4951], [0.2] * 5):
        assert sum(cell_counts(shares, 100)) == 100


def test_cells_fill_rows_from_the_top_left_in_slice_order():
    ring = donut_rings(discharge(), "destination", "patients", None)[0]
    drawn = cells(waffle_drawing({"ring": ring}, Box(0, 0, 400, 200), fake_measure, STYLE))
    assert len(drawn) == 100
    assert [shape["series"] for shape in drawn[:3]] == ["Home"] * 3 and drawn[-1]["series"] == "Died"
    tops = [shape["points"][0][1] for shape in drawn]
    lefts = [shape["points"][0][0] for shape in drawn]
    assert tops == sorted(tops) and lefts[:10] == sorted(lefts[:10]) and tops[9] < tops[10]
    assert drawn[0]["tip"] == "Home: 55%"


def test_key_names_every_slice_with_its_share():
    ring = donut_rings(discharge(), "destination", "patients", None)[0]
    shapes = waffle_drawing({"ring": ring}, Box(0, 0, 400, 200), fake_measure, STYLE)
    texts = [shape["text"] for shape in shapes if shape["kind"] == "text"]
    assert texts == ["Home", "55%", "Rehab", "22%", "Ward", "13%", "Care home", "7%", "Died", "3%"]


def test_a_narrow_figure_shrinks_the_grid_for_the_key():
    ring = donut_rings(discharge(), "destination", "patients", None)[0]
    wide = cells(waffle_drawing({"ring": ring}, Box(0, 0, 400, 200), fake_measure, STYLE))
    narrow = cells(waffle_drawing({"ring": ring}, Box(0, 0, 150, 200), fake_measure, STYLE))
    side = hl.load_tokens()["waffle"]

    def grid(drawn):
        return drawn[-1]["points"][2][0] - drawn[0]["points"][0][0]
    assert grid(wide) == pytest.approx(400 * side["grid_share"])
    assert 150 * side["min_grid_share"] <= grid(narrow) < 150 * side["grid_share"]


def test_more_than_seven_slices_fold_into_other():
    data = pd.DataFrame({"unit": [f"Unit {index}" for index in range(9)], "n": [9, 8, 7, 6, 5, 4, 3, 2, 1]})
    ring = donut_rings(data, "unit", "n", None, chart="waffle")[0]
    assert ring[-1]["name"] == "Other" and len(ring) == 7


def test_a_key_too_narrow_names_the_waffle():
    ring = donut_rings(discharge(), "destination", "patients", None)[0]
    with pytest.raises(hl.HairlineLayoutError, match="hairline: waffle: the key name"):
        waffle_drawing({"ring": ring}, Box(0, 0, 60, 60), fake_measure, STYLE)


def test_waffle_needs_values_above_zero():
    with pytest.raises(ValueError, match="hairline: waffle: no values above zero"):
        hl.waffle(pd.DataFrame({"a": ["x", "y"], "n": [0, 0]}), "a", "n")
