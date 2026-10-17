import math

import pandas as pd
import pytest
from test_donut import STYLE, fake_measure

import hairline as hl
from hairline.charts.forest import forest_spec
from hairline.charts.forest_geometry import forest_drawing, log_breaks
from hairline.layout.geometry import Box

FOREST_STYLE = {**STYLE, "data_width": 1.26, "axis_width": 0.585}


def studies():
    return pd.DataFrame({"study": ["Adams 2019", "Baker 2020", "Chen 2021", "Diaz 2022"],
                         "or": [0.62, 0.81, 0.47, 1.05], "low": [0.41, 0.55, 0.25, 0.70],
                         "high": [0.94, 1.19, 0.88, 1.58], "weight": [31.0, 27.0, 12.0, 30.0],
                         "n1": [120, 98, 45, 110], "n2": [118, 101, 47, 108]})


def drawing(**options):
    spec = forest_spec(studies(), "study", "or", "low", "high", weight="weight", columns={"n": "n1"},
                       pooled={"estimate": 0.72, "low": 0.58, "high": 0.89, "label": "Pooled"},
                       favours=("Favours early", "Favours standard"), color="#2474cf", **options)
    return spec, forest_drawing(spec, Box(0, 0, 480, 220), fake_measure, FOREST_STYLE)


def squares(shapes):
    return [shape for shape in shapes if shape.get("role") == "square"]


def width(shape):
    xs = [point[0] for point in shape["points"]]
    return max(xs) - min(xs)


def test_square_area_follows_weight():
    _, shapes = drawing()
    sides = [width(shape) for shape in squares(shapes)]
    assert (sides[0] / sides[2]) ** 2 == pytest.approx(31 / 12, rel=1e-6)


def test_ratio_axis_is_logarithmic():
    spec, shapes = drawing()
    ticks = {shape["text"]: shape["x"] for shape in shapes if shape.get("part") == "tick"}
    assert ticks["1"] - ticks["0.5"] == pytest.approx(ticks["2"] - ticks["1"]) if "2" in ticks else True
    assert spec["axis"]["breaks"] == log_breaks(0.25, 1.58)


def test_log_breaks_follow_one_two_five():
    assert log_breaks(0.25, 1.58) == [0.2, 0.5, 1, 2]
    assert log_breaks(0.03, 40) == [0.01, 0.1, 1, 10, 100]


def test_nonpositive_limit_on_ratio_scale_is_named():
    data = studies()
    data.loc[2, "low"] = 0
    with pytest.raises(ValueError, match="'Chen 2021' has a limit of 0 or below on a ratio scale"):
        forest_spec(data, "study", "or", "low", "high", color="#2474cf")


def test_table_rows_align_with_plot_rows():
    _, shapes = drawing()
    names = [shape for shape in shapes if shape["kind"] == "text" and shape["text"].endswith(("2019", "2022"))]
    centres = [sum(point[1] for point in shape["points"]) / 4 for shape in squares(shapes)]
    cap = FOREST_STYLE["cap_height"] * FOREST_STYLE["sizes"]["label"] / 2
    assert names[0]["y"] - cap == pytest.approx(centres[0], abs=0.5)
    assert names[1]["y"] - cap == pytest.approx(centres[3], abs=0.5)


def test_favours_labels_sit_either_side_of_null():
    spec, shapes = drawing()
    null_x = next(shape["points"][0][0] for shape in shapes if shape.get("part") == "null")
    favours = [shape for shape in shapes if shape.get("part") == "favours"]
    assert favours[0]["align"] == "right" and favours[0]["x"] < null_x
    assert favours[1]["align"] == "left" and favours[1]["x"] > null_x


def test_forest_figure_puts_heterogeneity_in_the_caption():
    figure = hl.forest(studies(), "study", "or", "low", "high", weight="weight", title="Mortality",
                       heterogeneity="I² = 18 %, tau² = 0.01", caption="Random effects.")
    assert figure.caption == "I² = 18 %, tau² = 0.01. Random effects."
    figure.figure.canvas.draw()
    assert figure.layout_report()["bare_panels"] == [0]
    assert math.isfinite(figure.layout_report()["drawing_texts"][0][0])
