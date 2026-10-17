import pandas as pd
import pytest
from test_donut import STYLE, fake_measure

import hairline as hl
from hairline.charts.sankey import sankey_spec
from hairline.charts.sankey_geometry import sankey_drawing
from hairline.layout.geometry import Box

COLUMNS = ["source", "account", "category"]


def budget():
    return pd.DataFrame({"source": ["Salary", "Salary", "Salary", "Salary", "Benefits", "Benefits", "Side job"],
                         "account": ["Joint", "Joint", "Savings", "Joint", "Joint", "Savings", "Joint"],
                         "category": ["Rent", "Food", "Reserve", "Leisure", "Food", "Reserve", "Leisure"],
                         "amount": [1200, 450, 400, 250, 150, 100, 200]})


def spec():
    return sankey_spec(budget(), COLUMNS, "amount")


def drawing():
    return sankey_drawing(spec(), Box(0, 0, 460, 240), fake_measure, STYLE)


def test_node_values_balance():
    nodes = spec()["nodes"]
    links = spec()["links"]
    for node in nodes[1]:
        incoming = sum(link["value"] for link in links if link["column"] == 0 and link["target"] == node["name"])
        outgoing = sum(link["value"] for link in links if link["column"] == 1 and link["source"] == node["name"])
        assert incoming == outgoing == node["value"]


def test_links_do_not_cross_inside_a_node():
    shapes = drawing()
    bands = [shape for shape in shapes if shape.get("role") == "link"]
    by_source = {}
    for band in bands:
        by_source.setdefault((band["column"], band["source"]), []).append(band)
    for group in by_source.values():
        starts = [(band["points"][0][1], band["points"][-1][1]) for band in group]
        ordered = sorted(starts)
        for (_, bottom), (top, _) in zip(ordered, ordered[1:], strict=False):
            assert top >= bottom - 1e-6


def test_outer_columns_label_away_from_the_nodes():
    shapes = drawing()
    nodes = {shape["name"]: shape for shape in shapes if shape.get("role") == "node"}
    labels = {shape["text"]: shape for shape in shapes if shape["kind"] == "text"}
    assert labels["Salary"]["align"] == "right" and labels["Salary"]["x"] < nodes["Salary"]["points"][0][0]
    assert labels["Rent"]["align"] == "left" and labels["Rent"]["x"] > nodes["Rent"]["points"][1][0]


def test_negative_value_is_named():
    data = budget()
    data.loc[1, "amount"] = -5
    with pytest.raises(ValueError, match="Salary → Joint → Food has a negative value"):
        sankey_spec(data, COLUMNS, "amount")


def test_needs_two_columns():
    with pytest.raises(ValueError, match="needs at least two columns"):
        sankey_spec(budget(), ["source"], "amount")


def test_sankey_figure_draws_headings():
    figure = hl.sankey(budget(), COLUMNS, "amount", title="Household budget",
                       headings=["Income", "Account", "Spending"])
    figure.figure.canvas.draw()
    texts = [shape["text"] for shape in figure.shapes if shape["kind"] == "text"]
    assert {"Income", "Account", "Spending"} <= set(texts)
