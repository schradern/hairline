import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from matplotlib.collections import PolyCollection

import hairline as hl
from hairline.charts.scatter_density import count_steps, hex_corners, hex_counts, hex_grid, nearest_cells
from hairline.interactive import figure_targets

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "hexagons.json").read_text(encoding="utf-8"))


def vitals(count: int = 600) -> pd.DataFrame:
    generator = np.random.default_rng(4)
    systolic = generator.normal(130, 18, count)
    return pd.DataFrame({"systolic": systolic, "diastolic": 0.5 * systolic + generator.normal(10, 6, count),
                         "unit": generator.choice(["North", "South", "East"], count)})


def hexagons(figure, index: int = 0) -> PolyCollection:
    return next(item for item in figure.axes[index].collections if isinstance(item, PolyCollection)
                and len(item.get_paths()) > 1)


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda case: f"{case['bins']}-{case['shape']}")
def test_hexagons_match_the_shared_fixture(case):
    x, y = np.array(case["x"]), np.array(case["y"])
    grid = hex_grid(x, y, case["bins"], "scatter", tuple(case["shape"]))
    assert grid == pytest.approx(case["grid"])
    cells = hex_counts(x, y, grid)
    assert [(cell["row"], cell["column"], cell["count"]) for cell in cells] == \
        [(cell["row"], cell["column"], cell["count"]) for cell in case["cells"]]
    assert [value for cell in cells for value in (cell["x"], cell["y"])] == \
        pytest.approx([value for cell in case["cells"] for value in (cell["x"], cell["y"])])
    assert [value for corner in hex_corners(cells[0], grid) for value in corner] == \
        pytest.approx([value for corner in case["corners"] for value in corner])


@pytest.mark.parametrize("case", FIXTURE["steps"], ids=lambda case: str(case["top"]))
def test_count_bins_match_the_shared_fixture(case):
    assert count_steps(case["top"]) == case["steps"]


def lattice_distance(x: float, y: float, row: int, column: int, grid: dict) -> float:
    """Squared distance from a point to a hexagon's centre on the regular lattice (centres one apart in a row)."""
    across = (x - grid["x0"]) / grid["width"] - (column + row % 2 / 2)
    up = ((y - grid["y0"]) / grid["height"] - row) * np.sqrt(3) / 2
    return across ** 2 + up ** 2


def test_every_point_lands_in_its_nearest_hexagon():
    generator = np.random.default_rng(3)
    x, y = generator.uniform(0, 50, 400), generator.uniform(0, 9, 400)
    grid = hex_grid(x, y, 9, "scatter")
    rows, columns = nearest_cells(x, y, grid)
    for index in range(len(x)):
        chosen = lattice_distance(x[index], y[index], rows[index], columns[index], grid)
        for row in range(rows[index] - 1, rows[index] + 2):
            for column in range(columns[index] - 1, columns[index] + 2):
                assert chosen <= lattice_distance(x[index], y[index], row, column, grid) + 1e-9


def test_density_counts_every_point_once():
    data = vitals()
    figure = hl.scatter(data, "systolic", "diastolic", density=True)
    targets = figure_targets(figure)["series"]
    counts = [int(tip["text"].split()[0]) for series in targets for tip in series["tips"]]
    assert sum(counts) == len(data)
    assert len(hexagons(figure).get_paths()) == len(counts)
    assert not [item for item in figure.axes[0].collections if type(item).__name__ == "PathCollection"]


def test_density_keys_its_bins_and_keeps_the_fit():
    figure = hl.scatter(vitals(), "systolic", "diastolic", density=12, colors="teals")
    assert figure.ramp_key["title"] == "Points per hexagon"
    assert [label for label, _ in figure.headers[0].stats] == ["n", "r", "Slope"]
    assert figure.description.startswith("Scatter plot with hexagonal bins. Linear fit: n = 600")


def test_density_facets_share_one_lattice_and_scale():
    figure = hl.scatter(vitals(), "systolic", "diastolic", density=True, facet="unit", fit=None)
    first, second = hexagons(figure, 0), hexagons(figure, 1)
    assert np.ptp(first.get_paths()[0].vertices[:, 0]) == pytest.approx(np.ptp(second.get_paths()[0].vertices[:, 0]))
    assert figure.description.endswith(f"Most points in one hexagon: {figure.description.split()[-1]}")


def test_density_is_german_in_a_german_figure():
    hl.use(brand=False, locale="de")
    try:
        figure = hl.scatter(vitals(), "systolic", "diastolic", density=True, fit=None)
        assert figure.ramp_key["title"] == "Punkte je Sechseck"
        tips = [tip["text"] for series in figure_targets(figure)["series"] for tip in series["tips"]]
        assert all(text.endswith(("Punkt", "Punkte")) for text in tips)
    finally:
        hl.use(brand=False)


@pytest.mark.parametrize(("options", "message"), [
    ({"by": "unit"}, "takes no by="),
    ({"colors": {"North": "#000000"}}, "colors must be a ramp name"),
    ({"density": 1}, "at least 2"),
    ({"density": 2.5}, "whole number"),
])
def test_density_refuses_what_it_cannot_draw(options, message):
    with pytest.raises(ValueError, match=message):
        hl.scatter(vitals(), "systolic", "diastolic", **{"density": True, **options})


def test_density_needs_a_spread_on_both_axes():
    flat = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [5.0, 5.0, 5.0, 5.0]})
    with pytest.raises(ValueError, match="spread along both axes"):
        hl.scatter(flat, "x", "y", density=True, fit=None)
