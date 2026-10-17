import json
import shutil

import matplotlib.colors as mcolors
import pytest

import hairline as hl
from hairline.entities import assign_colors

DAYLIGHT = hl.load_tokens()["palettes"]["daylight"]


def test_automatic_colours_are_stable_across_figures():
    hl.use()
    assert hl.color("Unit A") == DAYLIGHT[0]
    assert hl.color("Unit D") == DAYLIGHT[1]
    assert hl.color("Unit A") == DAYLIGHT[0]
    assert hl.colors() == {"Unit A": DAYLIGHT[0], "Unit D": DAYLIGHT[1]}


def test_explicit_colours_take_their_slot_and_are_skipped_by_automatic():
    hl.use(colors={"Unit B": DAYLIGHT[0]})
    assert hl.color("Unit A") == DAYLIGHT[1]
    assert hl.color("Unit B") == DAYLIGHT[0]


def test_use_starts_a_new_assignment():
    hl.use()
    hl.color("Sepsis")
    hl.use()
    assert hl.colors() == {}


def test_running_out_of_slots_names_the_entities():
    hl.use(palette=["#112233", "#445566"])
    hl.color("a")
    hl.color("b")
    with pytest.raises(ValueError, match="custom palette has 2 slots but 3 categories need colours: a, b, c"):
        hl.color("c")


def test_plain_matplotlib_series_follow_their_entity():
    hl.use()
    first = hl.figure("First")
    first.ax.plot([0, 1], [0, 1], label="Unit D")
    first.figure.canvas.draw()
    second = hl.figure("Second")
    line_m = second.ax.plot([0, 1], [0, 1], label="Unit A")[0]
    line_o = second.ax.plot([0, 1], [1, 0], label="Unit D")[0]
    custom = second.ax.plot([0, 1], [0.5, 0.5], label="Target", color="#123456")[0]
    second.figure.canvas.draw()
    assert mcolors.to_hex(line_o.get_color()) == DAYLIGHT[0]
    assert mcolors.to_hex(line_m.get_color()) == DAYLIGHT[1]
    assert mcolors.to_hex(custom.get_color()) == "#123456"


def test_brand_file_colours(tmp_path, repo_root):
    path = tmp_path / "_brand.yml"
    shutil.copy(repo_root / "brands" / "example" / "_brand.yml", path)
    path.write_text(path.read_text() + "    colors:\n      Unit B: poppy\n")
    hl.use(brand=path)
    brand_colors = hl.current_settings().palette
    assert hl.color("Unit B") == brand_colors[1]
    assert hl.color("Unit A") == brand_colors[0]


def test_brand_colour_must_exist(tmp_path, repo_root):
    path = tmp_path / "_brand.yml"
    shutil.copy(repo_root / "brands" / "example" / "_brand.yml", path)
    path.write_text(path.read_text() + "    colors:\n      Unit B: lavender\n")
    with pytest.raises(ValueError, match=r"defaults.hairline.colors.Unit B: 'lavender' is not in color.palette"):
        hl.use(brand=path)


def test_fixture_cases(repo_root):
    for case in json.loads((repo_root / "tokens/fixtures/entities.json").read_text()):
        if "error" in case:
            with pytest.raises(ValueError, match=case["error"]):
                assign_colors(case["palette"], case["label"], case["fixed"], case["requests"])
        else:
            assert assign_colors(case["palette"], case["label"], case["fixed"], case["requests"]) == case["expected"]
