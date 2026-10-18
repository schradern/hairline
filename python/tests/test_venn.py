import math

import pandas as pd
import pytest
from test_donut import STYLE, fake_measure

import hairline as hl
from hairline.charts.venn import venn_spec
from hairline.charts.venn_geometry import lens_area, separation, venn_drawing
from hairline.layout.geometry import Box

SETS = {"Diabetes": ["a", "b", "c", "d", "e"], "Hypertension": ["c", "d", "e", "f"], "Obesity": ["e", "f", "g"]}


def regions(spec):
    return {tuple(region["sets"]): region["value"] for region in spec["regions"]}


def test_named_sets_count_each_region_exactly_once():
    spec = venn_spec(SETS)
    assert regions(spec) == {(0,): 2, (1,): 0, (2,): 1, (0, 1): 2, (0, 2): 0, (1, 2): 1, (0, 1, 2): 1}
    assert [entry["value"] for entry in spec["sets"]] == [5, 4, 3]


def test_membership_columns_count_rows_and_reject_other_values():
    data = pd.DataFrame({"smoker": [1, 1, 0, 0], "obese": [True, False, True, False]})
    spec = venn_spec(data, ["smoker", "obese"])
    assert regions(spec) == {(0,): 1, (1,): 1, (0, 1): 1}
    assert [entry["name"] for entry in spec["sets"]] == ["Smoker", "Obese"]
    with pytest.raises(ValueError, match="'smoker' needs TRUE/FALSE or 0/1"):
        venn_spec(data.assign(smoker=["yes", "no", "no", "no"]), ["smoker", "obese"])


def test_set_counts_outside_two_or_three_are_refused_with_a_way_out():
    with pytest.raises(ValueError, match="4 sets given .* at most 3 fit .* bars"):
        venn_spec({**SETS, "Asthma": ["a"]})
    with pytest.raises(ValueError, match="1 set given"):
        venn_spec({"Diabetes": ["a"]})
    with pytest.raises(ValueError, match="proportional areas need two sets"):
        venn_spec(SETS, proportional=True)


def test_proportional_circles_overlap_by_the_shared_count():
    assert lens_area(1.0, 1.0, 0.0) == pytest.approx(math.pi)
    assert lens_area(1.0, 0.5, 2.0) == 0.0
    rules = hl.load_tokens()["venn"]
    distance = separation(1.0, 0.7, 0.4, rules)
    assert lens_area(1.0, 0.7, distance) == pytest.approx(0.4, abs=1e-9)


def test_drawing_fits_the_box_with_counts_inside_and_names_outside():
    spec = venn_spec(SETS)
    box = Box(10, 20, 420, 260)
    shapes = venn_drawing(spec, box, fake_measure, STYLE)
    circles = [shape for shape in shapes if shape.get("role") == "set"]
    assert len(circles) == 3
    points = [point for shape in shapes if shape["kind"] != "text" for point in shape["points"]]
    assert min(x for x, _ in points) >= box.x - 1e-6 and max(x for x, _ in points) <= box.x + box.width + 1e-6
    assert min(y for _, y in points) >= box.y - 1e-6 and max(y for _, y in points) <= box.y + box.height + 1e-6
    texts = [shape["text"] for shape in shapes if shape["kind"] == "text"]
    assert texts.count("0") == 2 and "Diabetes" in texts and "5" in texts


def test_proportional_drawing_skips_empty_regions():
    spec = venn_spec({"A": list(range(10)), "B": list(range(10, 14))}, proportional=True)
    texts = [shape["text"] for shape in venn_drawing(spec, Box(0, 0, 400, 240), fake_measure, STYLE)
             if shape["kind"] == "text"]
    assert "0" not in texts


def test_venn_returns_a_titled_figure():
    result = hl.venn(SETS)
    assert result.title == "Overlap of Diabetes, Hypertension and Obesity"
