import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import hairline as hl
from hairline.charts.heatmap import cell_edges, heatmap_spec
from hairline.charts.heatmap_geometry import heatmap_layout, heatmap_scene
from hairline.charts.surface import surface_spec
from hairline.charts.surface_geometry import pair_layout, surface_scene
from hairline.interactive import figure_targets
from hairline.layout.geometry import Box

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "heatmap.json").read_text(encoding="utf-8"))
SCENE_SCRIPT = Path(__file__).parents[1] / "src" / "hairline" / "data" / "interactive" / "hairline-scene.js"


def fake_measure(text, role, weight=None):
    return 0.5 * FIXTURE["style"]["sizes"][role] * len(text)


def frame_of(case):
    return pd.DataFrame({key: [np.nan if value is None else value for value in values]
                         for key, values in case["data"].items()})


def flat(shapes):
    return [value for shape in shapes for value in
            ([shape["x"], shape["y"]] if shape["kind"] == "text" else [v for point in shape["points"] for v in point])]


def grid():
    rows = [(hour, week, 0.5 + 0.3 * np.exp(-((hour - 12) / 3) ** 2) + 0.01 * week) for week in range(1, 9)
            for hour in range(6, 23)]
    return pd.DataFrame(rows, columns=["hour", "week", "share"])


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda case: f"{case['percent']}-{case['gradient']}")
def test_heatmap_spec_and_shapes_match_the_shared_fixture(case):
    hl.use(brand=False)
    spec = heatmap_spec(frame_of(case), "hour", "week", "load", titles=case["titles"], percent=case["percent"],
                        gradient=case["gradient"])
    assert spec["fills"] == case["spec"]["fills"] and spec["tips"] == case["spec"]["tips"]
    assert spec["ticks"] == case["spec"]["ticks"] and spec["key"] == case["spec"]["key"]
    shapes, cells = heatmap_layout(heatmap_scene(spec, fake_measure, FIXTURE["style"]), Box(*case["box"]),
                                   case["height"])
    assert flat(shapes) == pytest.approx(flat(case["shapes"]), abs=1e-6)
    assert [shape.get("tip") for shape in shapes] == [shape.get("tip") for shape in case["shapes"]]
    assert [value for cell in cells for value in cell] == pytest.approx(
        [value for cell in case["cells"] for value in cell], abs=1e-6)


def test_surface_and_heatmap_side_by_side_match_the_shared_fixture():
    hl.use(brand=False)
    pair = FIXTURE["pair"]
    spec = surface_spec(frame_of(pair), "hour", "week", "load", titles=pair["titles"], heatmap=True)
    assert spec["flat"]["fills"] == pair["spec"]["flat"]["fills"]
    layout = pair_layout(surface_scene(spec, fake_measure, FIXTURE["style"]),
                         heatmap_scene(spec["flat"], fake_measure, FIXTURE["style"]), Box(*pair["box"]))
    assert flat(layout["shapes"]) == pytest.approx(flat(pair["shapes"]), abs=1e-6)
    # Beside a surface the cells carry no tooltips of their own: the surface's script links the two.
    assert not any("tip" in shape for shape in layout["shapes"])
    heat = [shape for shape in layout["shapes"] if shape["kind"] != "text"]
    surface_bottom = max(point[1] for shape in heat[: -len(layout["cells"])] for point in shape["points"])
    assert layout["flat_box"].y + layout["flat_box"].height >= surface_bottom - 1e-6


def test_the_scene_script_finds_each_grid_point_where_the_surface_draws_it():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    hl.use(brand=False)
    pair = FIXTURE["pair"]
    spec = surface_spec(frame_of(pair), "hour", "week", "load", titles=pair["titles"], heatmap=True)
    scene = surface_scene(spec, fake_measure, FIXTURE["style"])
    script = (f"const shapes = require({json.dumps(str(SCENE_SCRIPT))});"
              "const c = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
              "const drawn = shapes(c.scene, c.box, c.scene.view, Infinity);"
              "console.log(JSON.stringify(drawn.cells.slice(0, 3).map(cell => cell.corners.map("
              "corner => [drawn.vertex(corner[0], corner[1]), cell.points[cell.corners.indexOf(corner)]]))));")
    given = json.dumps({"scene": scene, "box": pair["surface_box"]})
    found = json.loads(subprocess.run([node, "-e", script], input=given, capture_output=True, text=True,
                                      check=True).stdout)
    for corners in found:
        for vertex, point in corners:
            assert vertex == pytest.approx(point, abs=1e-9)


def test_cell_edges_lie_halfway_between_values_and_half_a_step_past_the_ends():
    assert cell_edges(np.array([1.0, 2.0, 4.0])).tolist() == [0.5, 1.5, 3.0, 5.0]


def test_heatmap_tags_one_series_per_row_and_lays_out_cleanly():
    hl.use(brand=False)
    figure = hl.heatmap(grid(), "hour", "week", "share", percent=True, y_title="Week")
    assert not hl.check_layout(figure)
    series = figure_targets(figure)["series"]
    assert [entry["name"] for entry in series][:2] == ["Week 1", "Week 2"]
    assert len(series[0]["tips"]) == 17 and series[0]["tips"][0]["text"].startswith("Hour 6, Week 1: ")


def test_surface_with_a_heatmap_sends_the_script_both_boxes_and_the_cells(tmp_path):
    hl.use(brand=False)
    figure = hl.surface(grid(), "hour", "week", "share", percent=True, heatmap=True)
    assert figure.size == "double" and not hl.check_layout(figure)
    scene = figure_targets(figure)["scenes"][0]
    assert len(scene["box"]) == 4 and len(scene["flat"]["cells"]) == 17 * 8
    assert scene["flat"]["box"][0] > scene["box"][0] + scene["box"][2]


def test_heatmap_refuses_a_grid_without_values():
    with pytest.raises(ValueError, match="'share' is missing in every row"):
        hl.heatmap(grid().assign(share=np.nan), "hour", "week", "share")
