import math

import pandas as pd
import pytest
from test_donut import fake_measure
from test_forest import FOREST_STYLE

import hairline as hl
from hairline.charts.funnel import funnel_spec
from hairline.charts.funnel_geometry import funnel_drawing
from hairline.charts.risk_of_bias import risk_of_bias_spec
from hairline.charts.risk_of_bias_geometry import risk_of_bias_drawing
from hairline.layout.geometry import Box

STYLE = {**FOREST_STYLE, "grid": 0.45}


def trials():
    return pd.DataFrame({"study": list("ABCDEFGH"), "or": [0.62, 0.81, 0.47, 1.05, 0.69, 0.4, 0.55, 0.9],
                         "se": [0.21, 0.19, 0.32, 0.2, 0.3, 0.45, 0.38, 0.15]})


def test_pooled_estimate_is_inverse_variance_weighted():
    spec = funnel_spec(trials(), "or", "se", ratio=True)
    weights = [1 / se ** 2 for se in trials()["se"]]
    expected = sum(w * math.log(v) for w, v in zip(weights, trials()["or"], strict=True)) / sum(weights)
    assert spec["pooled"] == pytest.approx(expected)


def test_funnel_apex_sits_on_the_pooled_line_at_zero_error():
    spec = funnel_spec(trials(), "or", "se", ratio=True)
    shapes = funnel_drawing(spec, Box(0, 0, 400, 260), fake_measure, STYLE)
    region = next(shape for shape in shapes if shape.get("role") == "funnel")
    pooled = next(shape for shape in shapes if shape.get("part") == "pooled")
    apex = min(region["points"], key=lambda point: point[1])
    assert apex[0] == pytest.approx(pooled["points"][0][0])
    assert len([shape for shape in shapes if shape.get("role") == "study"]) == 8


def test_funnel_reports_eggers_test():
    figure = hl.funnel(trials(), "or", "se")
    stats = dict(figure.headers[0].stats)
    assert stats["Egger"].startswith("p ")


def test_risk_of_bias_counts_judgements_per_domain():
    data = pd.DataFrame({"study": ["A", "A", "B", "B", "C", "C"], "domain": ["Randomisation", "Outcome"] * 3,
                         "judgement": ["Low", "Some concerns", "low", "High", "High risk", "Low risk"]})
    spec = risk_of_bias_spec(data, "study", "domain", "judgement")
    assert spec["domains"] == ["Randomisation", "Outcome", "Overall"]
    assert spec["counts"][0] == [2, 0, 1] and spec["counts"][1] == [1, 1, 1]
    assert spec["counts"][2] == [0, 1, 2]


def test_risk_of_bias_reads_a_wide_table_and_names_unknown_judgements():
    wide = pd.DataFrame({"study": ["A", "B"], "Randomisation": ["Low", "High"], "Outcome": ["Low", "Low"]})
    spec = risk_of_bias_spec(wide, "study", domains=["Randomisation", "Outcome"])
    assert spec["counts"][0] == [1, 0, 1]
    with pytest.raises(ValueError, match="judgement 'Maybe' for A, Outcome is not low, some concerns or high"):
        risk_of_bias_spec(wide.assign(Outcome=["Maybe", "Low"]), "study", domains=["Randomisation", "Outcome"])


def test_risk_of_bias_drawing_separates_overall():
    wide = pd.DataFrame({"study": ["A", "B", "C"], "Randomisation": ["Low", "High", "Low"],
                         "Outcome": ["Low", "Some", "Low"]})
    shapes = risk_of_bias_drawing(risk_of_bias_spec(wide, "study", domains=["Randomisation", "Outcome"]),
                                  Box(0, 0, 400, 200), fake_measure, STYLE)
    rules = [shape for shape in shapes if shape.get("part") == "rule"]
    assert len(rules) == 1
    texts = {shape["text"] for shape in shapes if shape["kind"] == "text"}
    assert texts >= {"Randomisation", "Outcome", "Overall", "2"}


def test_every_study_sits_inside_the_plot():
    spec = funnel_spec(trials(), "or", "se", ratio=True)
    shapes = funnel_drawing(spec, Box(0, 0, 400, 260), fake_measure, STYLE)
    axis = max(shape["points"][0][1] for shape in shapes if shape["kind"] == "line" and shape.get("part") is None
               and shape["points"][0][1] == shape["points"][1][1] and shape["color"] == STYLE["neutral"]["axis"])
    lowest = max(max(point[1] for point in shape["points"]) for shape in shapes if shape.get("role") == "study")
    assert lowest <= axis + STYLE["base"]
