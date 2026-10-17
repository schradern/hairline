import warnings

import pandas as pd
import pytest
from test_donut import fake_measure
from test_forest import FOREST_STYLE

import hairline as hl
from hairline.charts.arcs import arcs_spec
from hairline.charts.arcs_geometry import arcs_drawing
from hairline.charts.prisma import prisma_spec
from hairline.charts.prisma_geometry import prisma_drawing
from hairline.drawing import content_bottom as drawn_bottom
from hairline.drawing import drawing_style
from hairline.layout.geometry import Box

STYLE = {**FOREST_STYLE, "grid": 0.45}
COUNTS = {"identified": 1240, "duplicates": 260, "screened": 980, "excluded": 860, "sought": 120,
          "not_retrieved": 10, "assessed": 110,
          "excluded_reasons": {"Wrong population": 40, "Wrong intervention": 31, "No control group": 21},
          "included": 18}


def test_prisma_draws_five_main_boxes_and_four_exclusion_boxes():
    shapes = prisma_drawing(prisma_spec(COUNTS), Box(0, 0, 460, 420), fake_measure, STYLE)
    assert len([shape for shape in shapes if shape.get("role") == "main"]) == 5
    assert len([shape for shape in shapes if shape.get("role") == "exclusion"]) == 4
    assert len([shape for shape in shapes if shape.get("role") == "arrow"]) == 8


def test_prisma_text_stays_inside_its_box():
    shapes = prisma_drawing(prisma_spec(COUNTS), Box(0, 0, 300, 420), fake_measure, STYLE)
    boxes = [shape for shape in shapes if shape.get("role") in ("main", "exclusion")]
    for item in (shape for shape in shapes if shape.get("part") == "box_text"):
        width = fake_measure(item["text"], "label")
        assert any(box["points"][0][0] <= item["x"] and item["x"] + width <= box["points"][1][0] + 1e-6
                   for box in boxes)


def test_prisma_phases_are_rotated_labels():
    shapes = prisma_drawing(prisma_spec(COUNTS), Box(0, 0, 460, 420), fake_measure, STYLE)
    phases = [shape for shape in shapes if shape.get("part") == "phase"]
    assert [shape["text"] for shape in phases] == ["Identification", "Screening", "Included"]
    assert all(shape["rotation"] == 90 for shape in phases)


def test_prisma_warns_when_counts_do_not_add_up():
    with pytest.warns(UserWarning, match="screened 970 is not identified 1,240 minus removed 260"):
        prisma_spec({**COUNTS, "screened": 970})
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        prisma_spec(COUNTS)


def test_prisma_needs_the_core_counts():
    with pytest.raises(ValueError, match="needs identified, screened and included"):
        prisma_spec({"identified": 10})


def transfers():
    return pd.DataFrame({"source": ["ED", "ED", "ED", "Ward", "ICU", "ICU", "Ward"],
                         "target": ["ICU", "Ward", "ICU", "ICU", "Ward", "Home", "Home"]})


def test_arcs_join_each_pair_once_and_width_follows_the_count():
    spec = arcs_spec(transfers(), "source", "target", None)
    shapes = arcs_drawing(spec, Box(0, 0, 400, 200), fake_measure, STYLE)
    lines = [shape for shape in shapes if shape.get("role") == "arc"]
    assert len(lines) == 6
    widths = {(shape["source"], shape["target"]): shape["width"] for shape in lines}
    assert widths[("ED", "ICU")] > widths[("ED", "Ward")]
    assert [shape["text"] for shape in shapes if shape.get("part") == "node"] == ["ED", "ICU", "Ward", "Home"]


def test_arc_figure_has_a_width_key_and_a_default_title():
    figure = hl.arcs(transfers(), "source", "target")
    figure.figure.canvas.draw()
    assert figure.title == "Count from source to target"
    assert any(shape.get("part") == "key" for shape in figure.shapes)


def content_bottom(figure):
    return drawn_bottom(figure.shapes, drawing_style(figure.settings))


@pytest.mark.parametrize("make", [
    lambda: hl.prisma(COUNTS, size="double"),
    lambda: hl.dotplot(pd.DataFrame({"unit": list("ABC"), "rate": [0.1, 0.2, 0.15]}), "unit", "rate", size="double"),
    lambda: hl.arcs(transfers(), "source", "target", size="double")])
def test_drawn_charts_fit_the_figure_height_to_their_content(make):
    figure = make()
    figure.figure.canvas.draw()
    box = figure.plot_boxes[0]
    assert box.y + box.height - content_bottom(figure) == pytest.approx(0, abs=1)
