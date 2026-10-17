import numpy as np
import pandas as pd
import pytest
from test_donut import STYLE, fake_measure

import hairline as hl
from hairline.charts.correlation import correlation_spec
from hairline.charts.correlation_geometry import correlation_drawing
from hairline.layout.geometry import Box


def patients():
    generator = np.random.default_rng(8)
    sofa = generator.uniform(2, 14, 90).round(1)
    return pd.DataFrame({"sofa": sofa, "lactate": (0.6 + 0.3 * sofa + generator.normal(0, 0.8, 90)).round(2),
                         "age": generator.normal(64, 12, 90).round(),
                         "length_of_stay": (2 + 0.5 * sofa + generator.gamma(2, 1.5, 90)).round(1),
                         "group": generator.choice(["Medical", "Surgical"], 90)})


def test_scatter_reports_n_r_and_slope():
    figure = hl.scatter(patients(), "sofa", "lactate")
    labels = [label for label, _ in figure.headers[0].stats]
    assert labels == ["n", "r", "Slope"]
    assert dict(figure.headers[0].stats)["n"] == "90"
    assert figure.title == "Lactate and sofa"


def test_scatter_draws_fit_line_and_band():
    figure = hl.scatter(patients(), "sofa", "lactate")
    assert len(figure.ax.lines) == 1 and len(figure.ax.collections) == 2
    assert figure.ax.lines[0].get_color() == figure.settings.neutral["ink"]


def test_scatter_without_fit_and_with_groups():
    figure = hl.scatter(patients(), "sofa", "lactate", by="group", fit=None)
    figure.figure.canvas.draw()
    assert not figure.ax.lines and figure.layout_report()["legend_labels"] == ["Surgical", "Medical"] or \
        figure.layout_report()["legend_labels"] == ["Medical", "Surgical"]


def test_correlation_draws_the_lower_triangle_with_names_on_the_diagonal():
    spec = correlation_spec(patients(), ["sofa", "lactate", "age", "length_of_stay"], "pearson")
    shapes = correlation_drawing(spec, Box(0, 0, 400, 300), fake_measure, STYLE)
    cells = [shape for shape in shapes if shape.get("role") == "cell"]
    names = [shape["text"] for shape in shapes if shape.get("part") == "name"]
    assert len(cells) == 6 and names == ["Sofa", "Lactate", "Age", "Length of stay"]
    side = cells[0]["points"][1][0] - cells[0]["points"][0][0]
    assert side <= 4 * STYLE["base"]


def test_correlation_values_and_text_contrast():
    spec = correlation_spec(patients(), ["sofa", "lactate", "age"], "pearson")
    assert spec["texts"][1][0].startswith("0.")
    shapes = correlation_drawing(spec, Box(0, 0, 400, 300), fake_measure, STYLE)
    values = [shape for shape in shapes if shape.get("part") == "value"]
    assert len(values) == 3


def test_correlation_figure_has_a_colour_key():
    figure = hl.correlation(patients(), ["sofa", "lactate", "age", "length_of_stay"])
    figure.figure.canvas.draw()
    assert figure.layout_report()["legend_labels"] == ["−1", "−0.5", "0", "0.5", "1"]
    assert figure.title == "Pearson correlations"


def test_correlation_needs_two_numeric_columns():
    with pytest.raises(ValueError, match="needs at least two numeric columns"):
        hl.correlation(pd.DataFrame({"a": [1, 2], "b": ["x", "y"]}))
