import pandas as pd
import pytest
from test_donut import STYLE, fake_measure, nested

import hairline as hl
from hairline.charts.donut import donut_rings
from hairline.charts.partition import partition_drawing
from hairline.layout.geometry import Box

BOX = Box(0, 0, 400, 160)


def drawing(rings, levels=("Destination", "Support")):
    return partition_drawing({"rings": rings, "levels": list(levels)}, BOX, fake_measure, STYLE)


def bars(shapes):
    return [shape for shape in shapes if shape["kind"] == "polygon"]


def span(shape):
    xs = [point[0] for point in shape["points"]]
    return min(xs), max(xs)


def test_children_span_their_parent():
    rings = donut_rings(nested(), None, "patients", ["route", "detail"])
    shapes = bars(drawing(rings))
    parents, children = shapes[:len(rings[0])], shapes[len(rings[0]):]
    for child, segment in zip(children, rings[1], strict=True):
        low, high = span(parents[segment["parent"]])
        assert low - 1.5 <= span(child)[0] and span(child)[1] <= high + 1.5


def test_inside_label_fallback():
    rings = donut_rings(pd.DataFrame({"a": ["Long name", "b", "c"], "n": [95.5, 4, 0.5]}), "a", "n", None)
    texts = [shape["text"] for shape in drawing(rings, ("Level",)) if shape["kind"] == "text"]
    assert "Long name 96%" in texts
    assert "b" in texts and "4%" in texts
    assert not any(text.startswith("c") or text == "1%" or text == "0%" for text in texts)


def test_level_names_head_each_row():
    rings = donut_rings(nested(), None, "patients", ["route", "detail"])
    texts = [shape["text"] for shape in drawing(rings) if shape["kind"] == "text"]
    assert texts.count("Destination") == 1 and texts.count("Support") == 1


def test_partition_figure_reports_its_labels():
    figure = hl.partition(nested(), ["route", "detail"], "patients", title="Discharge",
                          level_names=["Destination", "Support"])
    figure.figure.canvas.draw()
    assert figure.layout_report()["bare_panels"] == [0]
    assert len(figure.layout_report()["drawing_texts"]) >= 2
    assert figure.layout_report()["legend_labels"] == ["Home", "Rehab", "Other"]


def test_level_names_must_match_levels():
    with pytest.raises(ValueError, match="2 levels but 1 level name"):
        hl.partition(nested(), ["route", "detail"], "patients", title="T", level_names=["Destination"])
