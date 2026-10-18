import math

import pandas as pd
import pytest
from test_donut import STYLE, fake_measure

import hairline as hl
from hairline.charts.chord import chord_spec
from hairline.charts.chord_geometry import chord_drawing
from hairline.layout.geometry import Box


def referrals():
    return pd.DataFrame({"origin": ["ED", "ED", "Ward", "Ward", "ICU", "ED", "Theatre", "ICU"],
                         "destination": ["ICU", "Ward", "ICU", "ED", "Ward", "ICU", "ICU", "Theatre"],
                         "patients": [40, 25, 18, 6, 22, 10, 30, 12]})


def test_pairs_combine_both_directions_and_nodes_sum_their_flows():
    spec = chord_spec(referrals(), "origin", "destination", "patients")
    links = {(link["source"], link["target"]): link["value"] for link in spec["links"]}
    assert links[("ED", "ICU")] == 50 and links[("ED", "Ward")] == 31
    totals = {node["name"]: node["value"] for node in spec["nodes"]}
    assert totals["ICU"] == 50 + 18 + 22 + 42


def test_arcs_follow_totals_and_ribbons_join_pairs():
    spec = chord_spec(referrals(), "origin", "destination", "patients")
    shapes = chord_drawing(spec, Box(0, 0, 420, 300), fake_measure, STYLE)
    arcs = [shape for shape in shapes if shape.get("role") == "node"]
    ribbons = [shape for shape in shapes if shape.get("role") == "ribbon"]
    assert len(arcs) == 4 and len(ribbons) == len(spec["links"])
    spans = {shape["name"]: shape["span"] for shape in arcs}
    totals = {node["name"]: node["value"] for node in spec["nodes"]}
    assert spans["ICU"] / spans["ED"] == pytest.approx(totals["ICU"] / totals["ED"])


def test_labels_name_each_group_with_its_total():
    spec = chord_spec(referrals(), "origin", "destination", "patients")
    texts = [shape["text"] for shape in chord_drawing(spec, Box(0, 0, 420, 300), fake_measure, STYLE)
             if shape["kind"] == "text"]
    assert {"ED", "ICU", "Ward", "Theatre"} <= set(texts) and "132" in texts


def test_chord_counts_rows_and_keeps_the_count_colours():
    figure = hl.chord(referrals().drop(columns="patients"), "origin", "destination")
    figure.figure.canvas.draw()
    fills = [shape["fill"] for shape in figure.shapes if shape.get("role") == "node"]
    assert fills == hl.palette()[:4]
    assert figure.title == "Count between origin and destination"
    assert math.isfinite(figure.layout_report()["drawing_texts"][0][0])
