import itertools
import json

import pytest

from hairline.color.adapt import adapt_readable
from hairline.color.check import check_palette
from hairline.color.space import hex_to_oklch
from hairline.color.vision import delta_e
from hairline.palettes import light_slots, palette, ramp

SHIPPED = ["daylight", "bloom", "citrus", "lagoon", "calm", "deep"]
BRAND_EXACT = ["#14325c", "#e8574f", "#8fc1f2", "#9ee0b4"]


@pytest.mark.parametrize("name", SHIPPED)
def test_shipped_palettes_pass(name):
    report = check_palette(palette(name))
    assert report.passed
    assert report.worst_cvd >= 8 and report.worst_normal >= 15 and report.head_all_pairs >= 8


def test_daylight_light_slots():
    assert check_palette(palette("daylight")).light_slots == [4, 5, 6, 8]
    assert light_slots(palette("daylight")) == [4, 5, 6, 8]


@pytest.mark.parametrize("name", SHIPPED)
def test_the_first_colours_form_the_most_readable_sets(name):
    """Two and three groups take the first two and three slots in every chart; each set stays readable."""
    colors = palette(name)
    for count in (2, 3):
        pairs = list(itertools.combinations(colors[:count], 2))
        assert min(delta_e(a, b, kind) for a, b in pairs for kind in ("protan", "deutan")) >= 8
        assert min(delta_e(a, b, None) for a, b in pairs) >= 15


def test_daylight_takes_no_light_slot_below_four_groups():
    assert not set(light_slots(palette("daylight"))) & {1, 2, 3}


def test_brand_exact_fails_band():
    report = check_palette(BRAND_EXACT)
    assert not report.passed
    assert any("lightness" in failure for failure in report.failures)


def test_adapt_readable_keeps_hue_and_passes():
    adapted = adapt_readable(BRAND_EXACT)
    assert check_palette(adapted).passed
    for given, used in zip(BRAND_EXACT, adapted, strict=True):
        assert abs(hex_to_oklch(given)[2] - hex_to_oklch(used)[2]) < 3


def test_adapt_leaves_passing_palette_alone():
    assert adapt_readable(palette("daylight")) == palette("daylight")


def test_too_many_categories():
    with pytest.raises(ValueError, match="palette 'daylight' has 8 slots but 9 categories"):
        palette("daylight", n=9)


def test_custom_palette_and_subset():
    assert palette(["#112233", "#445566"]) == ["#112233", "#445566"]
    assert palette("deep", n=3) == ["#2b5591", "#da6d5d", "#3c88b8"]


def test_unknown_palette_lists_names():
    with pytest.raises(ValueError, match="unknown palette 'sunset'.*daylight"):
        palette("sunset")


@pytest.mark.parametrize("name", ["blues", "teals", "oranges", "berries", "greys"])
def test_sequential_ramps_monotone(name):
    lightness = [hex_to_oklch(color)[0] for color in ramp(name)]
    assert lightness == sorted(lightness, reverse=True) and len(lightness) == 7


def test_diverging_ramp_has_grey_midpoint():
    colors = ramp("blue-coral")
    assert len(colors) == 13 and colors[6] == "#efefed"


def test_ramp_interpolates_other_counts():
    assert len(ramp("blues", n=4)) == 4 and ramp("blues", n=7) == ramp("blues")


def test_fixture_cases(repo_root):
    cases = json.loads((repo_root / "tokens/fixtures/checks.json").read_text())
    for case in cases["checks"]:
        report = check_palette(case["colors"], pairs=case["pairs"])
        assert report.passed == case["passed"] and report.light_slots == case["light_slots"]
        assert report.worst_cvd == pytest.approx(case["worst_cvd"], abs=1e-6)
    for case in cases["adapt"]:
        assert adapt_readable(case["colors"]) == case["adapted"]
