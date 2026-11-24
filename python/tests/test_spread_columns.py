import numpy as np
import pandas as pd
import pytest
from test_spread import STYLE, measure

import hairline as hl
from hairline.charts.spread import spread_spec
from hairline.charts.spread_geometry import spread_drawing, spread_layout
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens


def wards(count=40):
    """A drawn measure and two written ones per ward; one ward has no visitors recorded."""
    generator = np.random.default_rng(4)
    data = pd.DataFrame({"ward": np.repeat(["North", "South", "East"], count),
                         "stay": np.round(generator.gamma(3, 2, count * 3), 1),
                         "age": np.round(generator.normal(60, 12, count * 3)),
                         "visitors": generator.poisson(3, count * 3).astype(float)})
    data.loc[data["ward"] == "East", "visitors"] = np.nan
    return data


def test_written_columns_follow_the_stats_after_the_key_numbers():
    spec = spread_spec(wards(), "ward", "stay", stats=("mean", "iqr", "n"), columns={"age": "Age (years)"})
    north = spec["rows"][0]
    assert [label for label, _ in north["pairs"]] == ["Mean", "IQR", "n", "Age (years)"]
    rows = wards()[wards()["ward"] == "North"]["age"]
    q1, q3 = np.percentile(rows, [25, 75])
    assert north["pairs"][3][1] == f"{rows.mean():.1f} ({q1:.0f}–{q3:.0f})"
    assert spec["headings"] == {3: "Age (years)"}
    assert "Age (years): Mean (IQR)." in spec["notes"]


def test_a_column_name_or_several_are_labelled_from_their_names():
    spec = spread_spec(wards(), "ward", "stay", stats=("median",), columns=["age", "visitors"])
    assert spec["headings"] == {1: "Age", 2: "Visitors"}
    assert [value for _, value in spec["rows"][0]["pairs"][1:]][0].count("(") == 0
    assert spread_spec(wards(), "ward", "stay", columns="age")["headings"] == {3: "Age"}


def test_a_group_without_values_in_a_column_writes_a_dash():
    spec = spread_spec(wards(), "ward", "stay", columns="visitors")
    east = next(row for row in spec["rows"] if row["name"] == "East")
    assert east["pairs"][-1] == ["Visitors", "–"]


def test_a_mark_stays_after_the_written_columns_so_they_line_up():
    spec = spread_spec(wards(), "ward", "stay", stats=("median",), columns="age", marks={"North": 5},
                       mark_label="Target")
    assert [label for label, _ in spec["rows"][0]["pairs"]] == ["Median", "Age", "Target"]
    assert [label for label, _ in spec["rows"][1]["pairs"]] == ["Median", "Age"]


def test_headings_sit_on_the_axis_titles_line_and_names_return_under_each_row():
    spec = {**spread_spec(wards(), "ward", "stay", stats=("median",), columns={"age": "Age"}, axis_title="Days"),
            "numbers": "auto"}
    rules = load_tokens()["spread"]
    wide = spread_layout(spec, Box(0, 0, 500, 200), measure, STYLE, rules)
    assert not wide["under"] and wide["headings"] == {0: "Median", 1: "Age"}
    texts = {shape["text"]: shape for shape in spread_drawing(spec, Box(0, 0, 500, 200), measure, STYLE)
             if shape["kind"] == "text"}
    assert "Age " not in texts and "Median " not in texts
    assert texts["Age"]["y"] == texts["Median"]["y"] == texts["Days"]["y"]
    assert (texts["Median"]["x"], texts["Age"]["x"]) == tuple(wide["lefts"])
    narrow = spread_layout({**spec, "numbers": "below"}, Box(0, 0, 500, 200), measure, STYLE, rules)
    assert narrow["under"] and narrow["headings"] == {}
    below = [shape["text"] for shape in spread_drawing({**spec, "numbers": "below"}, Box(0, 0, 500, 200), measure,
                                                       STYLE) if shape["kind"] == "text"]
    assert below.count("Age ") == 3 and "Age" not in below


def test_without_written_columns_every_row_keeps_its_labels():
    spec = {**spread_spec(wards(), "ward", "stay", stats=("median", "n"), axis_title="Days"), "numbers": "auto"}
    layout = spread_layout(spec, Box(0, 0, 500, 200), measure, STYLE, load_tokens()["spread"])
    assert layout["headings"] == {}
    texts = [shape["text"] for shape in spread_drawing(spec, Box(0, 0, 500, 200), measure, STYLE)
             if shape["kind"] == "text"]
    assert texts.count("Median ") == 3 and "Median" not in texts


def test_comparisons_are_named_on_the_same_line_as_the_other_columns():
    spec = {**spread_spec(wards(), "ward", "stay", stats=("median",), columns="age", compare="North"),
            "numbers": "right"}
    layout = spread_layout(spec, Box(0, 0, 600, 200), measure, STYLE, load_tokens()["spread"])
    assert list(layout["headings"].values())[:2] == ["Median", "Age"] and len(layout["headings"]) == 4


def test_written_columns_work_in_facets_and_lay_out_cleanly():
    data = wards().assign(year=np.tile(["2024", "2025"], 60))
    figure = hl.spread(data, "ward", "stay", facet="year", columns={"age": "Age"}, size="double")
    assert hl.check_layout(figure) == []


def test_written_columns_are_numbers():
    with pytest.raises(ValueError, match="'ward' holds"):
        spread_spec(wards(), "ward", "stay", columns="ward")
    with pytest.raises(ValueError, match="column 'weight' is not in the data"):
        spread_spec(wards(), "ward", "stay", columns="weight")
