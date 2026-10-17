import pandas as pd
import pytest

import hairline as hl
from hairline.charts.donut import donut_rings
from hairline.charts.donut_geometry import donut_drawing
from hairline.color.tints import tints
from hairline.layout.geometry import Box

STYLE = {"base": 9.0, "sizes": {"title": 13.5, "panel": 9.0, "label": 7.2, "caption": 7.2}, "line_gap": 0.25,
         "cap_height": 0.7, "descender": 0.21,
         "neutral": {"ink": "#1b1e22", "muted": "#5b6168", "faint": "#6f757d", "axis": "#c4c8cd",
                     "surface": "#ffffff", "band": "#f2f3f5", "grid": "#eef0f2"},
         "swatch": 0.85, "swatch_text": 0.5, "leader_width": 0.54}


def fake_measure(text, role, weight=None):
    return 0.5 * STYLE["sizes"][role] * len(text)


def discharge():
    return pd.DataFrame({"destination": ["Home", "Rehab", "Ward", "Care home", "Died"],
                         "patients": [412, 168, 97, 54, 23]})


def nested():
    return pd.DataFrame({"route": ["Home", "Home", "Rehab", "Rehab", "Other"],
                         "detail": ["Alone", "With support", "Inpatient", "Outpatient", "Other"],
                         "patients": [250, 162, 120, 48, 77]})


def texts(primitives):
    return [item for item in primitives if item["kind"] == "text"]


def test_donut_shares_sum_to_one():
    rings = donut_rings(discharge(), "destination", "patients", None)
    assert sum(segment["share"] for segment in rings[0]) == pytest.approx(1)


def test_more_than_seven_slices_fold_into_other():
    data = pd.DataFrame({"name": list("abcdefghij"), "value": range(10, 0, -1)})
    rings = donut_rings(data, "name", "value", None)
    assert [segment["name"] for segment in rings[0]] == list("abcdef") + ["Other"]


def test_outside_labels_do_not_overlap():
    rings = donut_rings(pd.DataFrame({"name": list("abcdef"), "value": [80, 2, 2, 2, 2, 12]}), "name", "value", None)
    primitives = donut_drawing({"rings": rings, "labels": "outside", "total": None, "total_label": None},
                               Box(0, 0, 400, 200), fake_measure, STYLE)
    names = [item for item in texts(primitives) if item["role"] == "label" and item["color"] == STYLE["neutral"]["ink"]]
    line = STYLE["sizes"]["label"] * (1 + STYLE["line_gap"])
    for side in ("left", "right"):
        ys = sorted(item["y"] for item in names if item["align"] == ("right" if side == "left" else "left"))
        assert all(b - a >= line - 1e-6 for a, b in zip(ys, ys[1:], strict=False))


def test_children_use_parent_tints():
    rings = donut_rings(nested(), None, "patients", ["route", "detail"])
    home = next(segment for segment in rings[0] if segment["name"] == "Home")
    children = [segment["color"] for segment in rings[1] if segment["parent"] == home["index"]]
    assert children == tints(home["color"], 2)


def test_ring_labels_skip_small_segments():
    rings = donut_rings(pd.DataFrame({"route": ["a", "a", "b"], "detail": ["x", "y", "z"], "n": [97, 2, 1]}),
                        None, "n", ["route", "detail"])
    primitives = donut_drawing({"rings": rings, "labels": "ring", "total": None, "total_label": None},
                               Box(0, 0, 300, 200), fake_measure, STYLE)
    labelled = " ".join(item["text"] for item in texts(primitives))
    assert "y" not in labelled.split() and "z" not in labelled.split()


def test_four_levels_are_refused():
    data = pd.DataFrame({"a": ["x"], "b": ["y"], "c": ["z"], "d": ["w"], "n": [1]})
    with pytest.raises(ValueError, match="at most 3 levels"):
        donut_rings(data, None, "n", ["a", "b", "c", "d"])


def test_negative_values_are_named():
    with pytest.raises(ValueError, match="'Rehab' has a negative value"):
        donut_rings(pd.DataFrame({"name": ["Home", "Rehab"], "value": [3, -1]}), "name", "value", None)


def test_donut_figure_reports_its_labels():
    figure = hl.donut(discharge(), "destination", "patients", title="Discharge destination", total_label="patients")
    figure.figure.canvas.draw()
    report = figure.layout_report()
    assert report["bare_panels"] == [0]
    assert len(report["drawing_texts"]) == 2 * 5 + 2
