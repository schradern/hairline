import logging
import shutil

import pytest
import yaml

import hairline as hl
from hairline.brand import brand_report, find_brand, load_brand

BRAND = {
    "meta": {"name": "Example University Hospital"},
    "color": {"palette": {"harbor": "#0b3d6e", "poppy": "#f2545b", "glacier": "#8cc8ff", "fern": "#7fd8a0"},
              "foreground": "harbor"},
    "defaults": {"hairline": {"categorical": ["harbor", "poppy", "glacier", "fern"], "adapt": "readable"}},
}


@pytest.fixture
def example(repo_root):
    return repo_root / "brands" / "example" / "_brand.yml"


def write_brand(folder, adapt="readable", categorical=None, **colors):
    content = yaml.safe_load(yaml.safe_dump(BRAND))
    content["color"]["palette"].update(colors)
    content["defaults"]["hairline"]["adapt"] = adapt
    if categorical is not None:
        content["defaults"]["hairline"]["categorical"] = categorical
    path = folder / "_brand.yml"
    path.write_text(yaml.safe_dump(content, sort_keys=False))
    return path


def test_example_brand_readable_passes(example):
    brand = load_brand(example)
    assert brand.name == "Example University Hospital" and brand.adapt == "readable"
    assert hl.check_palette(brand.colors_used).passed
    assert brand.neutral["ink"] == "#0b3d6e" and brand.sizes == {"title": 14} and brand.locale == "de"


def test_exact_mode_warns_about_light_slots(tmp_path):
    with pytest.warns(UserWarning, match="glacier.*below 3:1"):
        brand = load_brand(write_brand(tmp_path, adapt="exact"))
    assert brand.colors_used == brand.colors_given


def test_bad_hex_message(tmp_path):
    with pytest.raises(ValueError, match=r"_brand.yml: color.palette.glacier: '#8cc8f' is not a 6-digit hex colour"):
        load_brand(write_brand(tmp_path, glacier="#8cc8f"))


def test_unknown_categorical_name(tmp_path):
    with pytest.raises(ValueError, match=r"defaults.hairline.categorical\[2\]: 'ice' is not in color.palette"):
        load_brand(write_brand(tmp_path, categorical=["harbor", "poppy", "ice"]))


def test_unknown_adapt_mode(tmp_path):
    with pytest.raises(ValueError, match=r"defaults.hairline.adapt: 'strict' must be 'exact' or 'readable'"):
        load_brand(write_brand(tmp_path, adapt="strict"))


def test_yaml_syntax_error(tmp_path):
    path = tmp_path / "_brand.yml"
    path.write_text("color:\n  palette: [unclosed\n")
    with pytest.raises(ValueError, match=r"_brand.yml: line \d+"):
        load_brand(path)


def test_auto_lookup_stops_at_project_root(tmp_path, example):
    project = tmp_path / "project"
    (project / "analysis" / "deep").mkdir(parents=True)
    (project / "pyproject.toml").write_text("")
    shutil.copy(example, tmp_path / "_brand.yml")
    assert find_brand(project / "analysis" / "deep") is None
    shutil.copy(example, project / "_brand.yml")
    assert find_brand(project / "analysis" / "deep") == project / "_brand.yml"


def test_use_finds_brand_and_announces_once(tmp_path, example, monkeypatch, caplog):
    shutil.copy(example, tmp_path / "_brand.yml")
    monkeypatch.chdir(tmp_path)
    with caplog.at_level(logging.INFO, logger="hairline"):
        settings = hl.use()
        hl.use()
    assert settings.brand_name == "Example University Hospital" and settings.locale == "de"
    assert sum("Using brand" in record.message for record in caplog.records) == 1


def test_explicit_arguments_beat_brand(tmp_path, example, monkeypatch):
    shutil.copy(example, tmp_path / "_brand.yml")
    monkeypatch.chdir(tmp_path)
    settings = hl.use(locale="en", palette="lagoon")
    assert settings.locale == "en" and settings.palette_name == "lagoon"


def test_use_brand_false_disables_lookup(tmp_path, example, monkeypatch):
    shutil.copy(example, tmp_path / "_brand.yml")
    monkeypatch.chdir(tmp_path)
    assert hl.use(brand=False).brand_name is None


def test_brand_slot_guard(example):
    hl.use(brand=example)
    with pytest.raises(ValueError, match="brand 'Example University Hospital' has 4 slots but 5 categories"):
        hl.palette(n=5)


def test_brand_report_lists_slots(example):
    report = brand_report(load_brand(example))
    assert "harbor" in report and "#0b3d6e" in report and "passed" in report




def layered_paths():
    from pathlib import Path
    folder = Path(__file__).resolve().parents[2] / "brands" / "example"
    return [folder / "_brand.yml", folder / "units.yml"]


def test_layers_merge_in_order_and_outputs_override_last():
    brand = load_brand(layered_paths(), output="docx")
    assert brand.name == "Example University Hospital, ICU project"
    assert brand.colors_given == load_brand(layered_paths()[0]).colors_given
    assert brand.base_size == 10
    assert load_brand(layered_paths(), output="html").neutral["grid"] == "#e6e8eb"
    assert load_brand(layered_paths()).base_size == 9


def test_pinned_colours_are_checked_and_groups_take_tints():
    import warnings
    brand = load_brand(layered_paths())
    assert set(brand.entity_colors) == {"Unit A", "Unit B", "Surgery", "Unit C", "Unit D"}
    assert brand.entity_colors["Unit C"] != brand.entity_colors["Unit D"]
    assert brand.entity_failures == []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        from hairline.brand_entities import checked_entities
        kept, failures = checked_entities({"Unit A": "#0b3d6e", "Unit B": "#1d4f86"}, "exact", "test")
    assert kept["Unit B"] == "#1d4f86" and failures and "Unit A / Unit B" in failures[0]
    assert any("hard to tell apart" in str(item.message) for item in caught)


def test_unknown_output_is_named():
    with pytest.raises(ValueError, match="output 'slides' must be one of screen, pdf, html, docx"):
        load_brand(layered_paths(), output="slides")


def test_use_takes_layers_and_an_output():
    settings = hl.use(brand=layered_paths(), output="docx")
    assert settings.base_size == 10
    assert hl.color("Unit C") == load_brand(layered_paths()).entity_colors["Unit C"]
    hl.use(brand=False)


def test_brand_report_reads_the_active_brand_as_in_r(example, monkeypatch):
    hl.use(brand=False)
    assert hl.brand_report() == "No brand is active."
    monkeypatch.chdir(example.parent)
    hl.use(brand="_brand.yml")
    assert hl.brand_report().startswith("Brand 'Example University Hospital'")
    assert f"layer 1: {example.resolve()}" in hl.brand_report().splitlines()
    hl.use(brand=False)


def test_the_report_names_the_layer_each_value_came_from(repo_root):
    folder = repo_root / "brands" / "example"
    report = hl.brand_report(load_brand([folder / "_brand.yml", folder / "units.yml"]))
    lines = report.splitlines()
    assert lines[1:3] == [f"layer {index}: {(folder / name).resolve()}"
                          for index, name in ((1, "_brand.yml"), (2, "units.yml"))]
    assert lines[3] == "slot  name        given    used     light  layer"
    assert lines[4].split()[-1] == "1"
    assert "entity Unit A: " in report and [line for line in lines if line.startswith("entity Unit A:")][0].endswith(
        "(layer 2)")


def test_an_export_override_is_named_with_its_layer(tmp_path):
    base, project = tmp_path / "_brand.yml", tmp_path / "project.yml"
    base.write_text('color:\n  palette:\n    harbor: "#0b3d6e"\n    poppy: "#f2545b"\n'
                    "defaults:\n  hairline:\n    categorical: [harbor, poppy]\n", encoding="utf-8")
    project.write_text("defaults:\n  hairline:\n    outputs:\n      docx:\n        colors:\n          Unit A: poppy\n",
                       encoding="utf-8")
    report = hl.brand_report(load_brand([base, project], output="docx"))
    assert [line for line in report.splitlines() if line.startswith("entity Unit A:")][0].endswith("(layer 2, docx)")
