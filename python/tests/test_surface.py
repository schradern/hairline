import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import hairline as hl
from hairline.charts.surface import color_steps, surface_spec
from hairline.charts.surface_geometry import scene_shapes, surface_scene
from hairline.errors import HairlineLayoutError
from hairline.layout.geometry import Box

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "surface.json").read_text(encoding="utf-8"))
SCENE_SCRIPT = Path(__file__).parents[1] / "src" / "hairline" / "data" / "interactive" / "hairline-scene.js"


def fake_measure(text, role, weight=None):
    return 0.5 * FIXTURE["style"]["sizes"][role] * len(text)


def grid(hours=range(6, 23), weeks=range(1, 9)):
    rows = [(hour, week, 0.5 + 0.3 * np.exp(-((hour - 12) / 3) ** 2) + 0.01 * week) for week in weeks
            for hour in hours]
    return pd.DataFrame(rows, columns=["hour", "week", "share"])


def points_of(shapes):
    return [value for shape in shapes for point in shape["points"] for value in point]


def flat(shapes):
    return [value for shape in shapes for value in
            ([shape["x"], shape["y"]] if shape["kind"] == "text" else [v for point in shape["points"] for v in point])]


@pytest.mark.parametrize("case", FIXTURE["cases"],
                         ids=lambda case: f"{case['percent']}-{case['gradient']}-{case['view']}")
def test_surface_spec_and_shapes_match_the_shared_fixture(case):
    hl.use(brand=False)
    data = pd.DataFrame({key: [np.nan if value is None else value for value in values]
                         for key, values in case["data"].items()})
    spec = surface_spec(data, "hour", "week", "load", titles=case["titles"], percent=case["percent"],
                        gradient=case["gradient"])
    assert spec["fills"] == case["spec"]["fills"] and spec["ticks"] == case["spec"]["ticks"]
    assert spec["key"] == case["spec"]["key"]
    assert spec["tips"] == case["spec"]["tips"]
    shapes = scene_shapes(surface_scene(spec, fake_measure, FIXTURE["style"]), Box(*case["box"]), case["view"])
    assert flat(shapes) == pytest.approx(flat(case["shapes"]), abs=1e-6)
    assert [shape.get("text") for shape in shapes] == [shape.get("text") for shape in case["shapes"]]


def test_a_gap_and_a_missing_value_leave_out_the_cells_they_touch():
    case = FIXTURE["cases"][0]
    cells = [shape for shape in case["shapes"] if shape.get("part") == "cell"]
    # 6 hours x 5 weeks: 20 cells; the missing pair (14, week 2) takes its four, the missing corner value (18, week 1)
    # its one.
    assert len(cells) == 20 - 4 - 1


def test_the_scene_script_draws_the_fixture_as_python_does():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    script = (f"const shapes = require({json.dumps(str(SCENE_SCRIPT))});"
              "const cases = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
              "console.log(JSON.stringify(cases.map(c => shapes(c.scene, c.box, c.view || c.scene.view, Infinity))));")
    found = json.loads(subprocess.run([node, "-e", script], input=json.dumps(FIXTURE["cases"]), capture_output=True,
                                      text=True, check=True).stdout)
    for case, drawn in zip(FIXTURE["cases"], found, strict=True):
        expected = {"line": [], "polygon": [], "text": []}
        for shape in case["shapes"]:
            expected[shape["kind"]].append(shape)
        for kind, items in (("line", drawn["lines"]), ("polygon", drawn["cells"])):
            assert points_of(items) == pytest.approx(points_of(expected[kind]), abs=1e-6)
        assert [cell["fill"] for cell in drawn["cells"]] == [cell["fill"] for cell in expected["polygon"]]
        assert [value for item in drawn["texts"] for value in (item["x"], item["y"])] == pytest.approx(
            [value for item in expected["text"] for value in (item["x"], item["y"])], abs=1e-6)


def test_colour_bins_are_half_a_tick_step_up_past_the_highest_value():
    assert color_steps([0.4, 0.6, 0.8], 0.87) == [0.5, 0.6, 0.7, 0.8, 0.9]
    assert color_steps([0, 50, 100], 100) == [25, 50, 75, 100]
    # Half steps would give the key seven squares; whole steps keep it to one row.
    assert color_steps([0.5, 0.6, 0.7, 0.8], 0.84) == [0.6, 0.7, 0.8, 0.9]


def test_surface_keys_its_bins_and_turns_in_html(tmp_path):
    hl.use(brand=False)
    figure = hl.surface(grid(), "hour", "week", "share", percent=True)
    assert figure.ramp_key["labels"][-1].endswith("%")
    assert not hl.check_layout(figure)
    path = hl.save(figure, tmp_path / "surface", formats=("html",))[0]
    html = path.read_text(encoding="utf-8")
    assert "var hairlineSceneShapes" in html and '"scenes":' in html


def test_a_gradient_blends_cells_along_the_ramp_and_keys_the_ticks():
    hl.use(brand=False)
    banded = surface_spec(grid(), "hour", "week", "share", titles={"x": "", "y": "", "z": ""})
    blended = surface_spec(grid(), "hour", "week", "share", titles={"x": "", "y": "", "z": ""}, gradient=True)
    colours = {fill for row in blended["fills"] for fill in row}
    assert len(colours) > len({fill for row in banded["fills"] for fill in row})
    assert blended["key"]["steps"] == [0.5, 0.6, 0.7, 0.8, 0.9]
    assert blended["key"]["colors"][-1] == hl.ramp("blues", 65)[-1]


def test_figures_without_a_surface_leave_the_scene_script_out(tmp_path):
    hl.use(brand=False)
    figure = hl.figure("Line")
    figure.ax.plot([0, 1], [0, 1])
    html = hl.save(figure, tmp_path / "line", formats=("html",))[0].read_text(encoding="utf-8")
    assert "var hairlineSceneShapes" not in html and '"scenes"' not in html


@pytest.mark.parametrize(("data", "message"), [
    (pd.concat([grid(), grid().head(1)]), "share an (hour, week) pair"),
    (grid(hours=[8]), "'hour' needs 2 to 150 distinct values"),
    (grid().assign(share=np.nan), "no cell of the grid"),
    (grid().assign(share="high"), "needs numbers"),
])
def test_surface_refuses_data_it_cannot_draw(data, message):
    with pytest.raises(ValueError, match=message.replace("(", r"\(").replace(")", r"\)")):
        hl.surface(data, "hour", "week", "share")


def test_surface_refuses_a_view_from_below_or_straight_above():
    with pytest.raises(ValueError, match="elevation 85 must lie between 10 and 80"):
        hl.surface(grid(), "hour", "week", "share", elevation=85)


def test_titles_too_wide_for_the_box_are_a_layout_error():
    spec = surface_spec(grid(), "hour", "week", "share", titles={"x": "x" * 200, "y": "y", "z": "z"})
    with pytest.raises(HairlineLayoutError, match="no room for the surface"):
        scene_shapes(surface_scene(spec, fake_measure, FIXTURE["style"]), Box(0, 0, 120, 90))
