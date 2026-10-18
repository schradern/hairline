import json
import shutil

import matplotlib.colors as mcolors
import pandas as pd
import pytest

import hairline as hl
from hairline import entities as hl_entities
from hairline.entities import assign_colors, chart_colors

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


def test_new_groups_in_a_later_chart_start_at_the_first_slot():
    hl.use()
    with hl_entities.chart(["Surgical", "Medical"]):
        pass
    with hl_entities.chart(["Female", "Male"]) as colours:
        assert colours == {"Female": DAYLIGHT[0], "Male": DAYLIGHT[1]}
    assert hl.color("Surgical") == DAYLIGHT[0]


def test_a_clash_only_moves_the_colour_within_that_chart():
    hl.use()
    with hl_entities.chart(["A"]):
        pass
    with hl_entities.chart(["X"]):
        pass
    with hl_entities.chart(["A", "X"]) as colours:
        assert colours == {"A": DAYLIGHT[0], "X": DAYLIGHT[1]}
    with hl_entities.chart(["X"]) as colours:
        assert colours == {"X": DAYLIGHT[0]}


def test_a_chart_override_is_not_remembered():
    hl.use()
    data = pd.DataFrame({"sex": ["Female", "Male", "Male"]})
    figure = hl.bars(data, "sex", by="sex", colors={"Male": "#123456"})
    faces = {mcolors.to_hex(patch.get_facecolor()) for patch in figure.ax.patches}
    assert "#123456" in faces and DAYLIGHT[0] in faces
    assert hl.colors().get("Male") != "#123456"


def test_chart_colours_rule():
    assert chart_colors(DAYLIGHT, "palette", {"F": "#000000"}, {"R": DAYLIGHT[1]}, {"O": "#ffffff"},
                        ["O", "F", "R", "N1", "N2"]) == {"O": "#ffffff", "F": "#000000", "R": DAYLIGHT[1],
                                                         "N1": DAYLIGHT[0], "N2": DAYLIGHT[2]}
