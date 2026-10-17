import pandas as pd
from test_donut import fake_measure
from test_forest import FOREST_STYLE

import hairline as hl
from hairline.charts.forest import forest_spec
from hairline.charts.forest_geometry import forest_drawing
from hairline.layout.geometry import Box


def units():
    return pd.DataFrame({"unit": ["A", "B", "C", "D"], "mortality": [0.12, 0.21, 0.08, 0.15],
                         "low": [0.09, 0.16, 0.05, 0.11], "high": [0.16, 0.27, 0.12, 0.2]})


def test_dot_plot_sorts_by_value_and_draws_circles():
    figure = hl.dotplot(units(), "unit", "mortality", "low", "high")
    figure.figure.canvas.draw()
    rows = [shape["text"] for shape in figure.shapes if shape["kind"] == "text" and shape["text"] in "ABCD"]
    assert rows == ["B", "D", "A", "C"]
    dots = [shape for shape in figure.shapes if shape.get("role") == "dot"]
    assert len(dots) == 4 and len(dots[0]["points"]) > 8


def test_dot_plot_without_intervals_labels_the_value():
    figure = hl.dotplot(units(), "unit", "mortality")
    figure.figure.canvas.draw()
    texts = [shape["text"] for shape in figure.shapes if shape["kind"] == "text"]
    assert "0.21" in texts and figure.title == "Mortality by unit"


def test_dot_marker_in_the_geometry():
    spec = forest_spec(units(), "unit", "mortality", "low", "high", ratio=False, color="#2474cf", marker="dot")
    shapes = forest_drawing(spec, Box(0, 0, 400, 160), fake_measure, FOREST_STYLE)
    assert any(shape.get("role") == "dot" for shape in shapes)
