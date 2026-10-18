import pandas as pd
import pytest

import hairline as hl
from hairline.charts.correlation import correlation_spec
from hairline.color.ramps import diverging_ramp, sequential_ramp
from hairline.color.space import hex_to_oklch
from hairline.tokens import load_tokens

EXPLICIT = """meta:
  name: Ramp test
color:
  palette:
    harbor: "#0b3d6e"
    poppy: "#f2545b"
    glacier: "#8cc8ff"
    fern: "#7fd8a0"
defaults:
  hairline:
    categorical: [harbor, poppy, glacier, fern]
    adapt: readable
    sequential: poppy
    diverging: [glacier, fern]
"""


@pytest.fixture(autouse=True)
def plain_settings():
    hl.use(brand=False)
    yield
    hl.use(brand=False)


@pytest.fixture
def example(repo_root):
    return repo_root / "brands" / "example" / "_brand.yml"


def hue(color):
    return hex_to_oklch(color)[2]


def test_the_ramp_rule_reproduces_the_token_ramps():
    tokens = load_tokens()
    definition = tokens["ramp_definitions"]
    for name, ramp_hue in definition["sequential"].items():
        assert sequential_ramp(ramp_hue) == tokens["ramps"][name]
    for name, (low, high) in definition["diverging"].items():
        assert diverging_ramp(low, high) == tokens["ramps"][name]


def test_a_brand_takes_its_ramps_from_its_first_colours(example):
    settings = hl.use(brand=example)
    used = settings.palette
    assert settings.ramps["brand-sequential"] == tuple(sequential_ramp(hue(used[0])))
    assert settings.ramps["brand-diverging"] == tuple(diverging_ramp(hue(used[0]), hue(used[1])))


def test_brand_ramp_hues_can_be_named(tmp_path):
    path = tmp_path / "_brand.yml"
    path.write_text(EXPLICIT, encoding="utf-8")
    settings = hl.use(brand=path)
    assert settings.ramps["brand-sequential"] == tuple(sequential_ramp(hue("#f2545b")))
    assert settings.ramps["brand-diverging"] == tuple(diverging_ramp(hue("#8cc8ff"), hue("#7fd8a0")))


def test_the_default_ramp_follows_the_brand(example):
    assert hl.ramp() == hl.ramp("blues")
    hl.use(brand=example)
    assert hl.ramp() == hl.ramp("brand-sequential") == list(hl.current_settings().ramps["brand-sequential"])
    assert hl.colormap().name == "brand-sequential"
    assert hl.ramp("blues") == load_tokens()["ramps"]["blues"]


def test_brand_ramps_need_a_brand():
    with pytest.raises(ValueError, match="unknown ramp 'brand-sequential'; available ramps: blues"):
        hl.ramp("brand-sequential")


def test_the_heatmap_uses_the_brand_diverging_ramp(example):
    data = pd.DataFrame({"a": [1, 2, 3, 4], "b": [2, 4, 5, 8], "c": [4, 3, 2, 1]})
    plain = correlation_spec(data, ["a", "b", "c"], "pearson")["colors"]
    hl.use(brand=example)
    branded = correlation_spec(data, ["a", "b", "c"], "pearson")["colors"]
    assert plain[2][0] == load_tokens()["ramps"]["blue-coral"][0]
    assert branded[2][0] == hl.current_settings().ramps["brand-diverging"][0]


def test_brand_ramps_join_the_catalogue_while_active(example):
    assert "brand-sequential" not in set(hl.palettes()["name"])
    hl.use(brand=example)
    table = hl.palettes()
    rows = table[table["name"].isin(["brand-sequential", "brand-diverging"])]
    assert list(rows["kind"]) == ["sequential", "diverging"]
    assert list(rows["slots"]) == [7, 13]
    figure = hl.swatches(["brand-sequential", "brand-diverging"])
    assert figure.title == "Colour sets"


def test_a_diverging_brand_entry_needs_two_colours(tmp_path):
    path = tmp_path / "_brand.yml"
    path.write_text('color:\n  palette:\n    harbor: "#0b3d6e"\ndefaults:\n  hairline:\n    diverging: [harbor]\n',
                    encoding="utf-8")
    with pytest.raises(ValueError, match="defaults.hairline.diverging: must list two colours"):
        hl.load_brand(path)


def test_a_google_font_names_the_font_and_the_fix(tmp_path):
    path = tmp_path / "_brand.yml"
    path.write_text("typography:\n  fonts:\n    - family: Source Serif 4\n      source: google\n", encoding="utf-8")
    expected = (r"'Source Serif 4' comes from Google Fonts, which hairline does not download; install it "
                r"\(https://fonts.google.com/specimen/Source\+Serif\+4\) or put its files next to the brand file "
                r"with source: file")
    with pytest.warns(UserWarning, match=expected):
        hl.load_brand(path)
