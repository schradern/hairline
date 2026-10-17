import json

import pytest

from hairline.color.space import hex_to_oklab, hex_to_oklch, oklch_to_hex
from hairline.color.vision import contrast, delta_e, simulate


def test_oklch_round_trip():
    for color in ["#2474cf", "#e8a628", "#14325c", "#ffffff", "#000000", "#6f757d"]:
        assert oklch_to_hex(*hex_to_oklch(color)) == color


def test_known_values():
    lightness, chroma, hue = hex_to_oklch("#14325c")
    assert (round(lightness, 3), round(chroma, 3), round(hue, 1)) == (0.319, 0.083, 257.4)
    assert round(contrast("#6f757d", "#ffffff"), 2) == 4.65
    assert round(contrast("#ffffff", "#6f757d"), 2) == 4.65


def test_gamut_clamp_keeps_hue_and_lightness():
    lightness, chroma, hue = hex_to_oklch(oklch_to_hex(0.65, 0.16, 195))
    assert abs(hue - 195) < 1.5 and abs(lightness - 0.65) < 0.01 and chroma < 0.16


def test_delta_e_is_scaled_oklab_distance():
    assert delta_e("#ffffff", "#000000") == pytest.approx(100, abs=0.1)
    assert delta_e("#2474cf", "#2474cf", "deutan") == 0


def test_simulation_collapses_red_green():
    assert delta_e("#d62728", "#2ca02c") > 30
    assert delta_e("#d62728", "#2ca02c", "deutan") < delta_e("#d62728", "#2ca02c") / 2


def test_bad_hex_message():
    with pytest.raises(ValueError, match="'#12345' is not a 6-digit hex colour"):
        hex_to_oklab("#12345")


def test_fixture_cases(repo_root):
    cases = json.loads((repo_root / "tokens/fixtures/colour.json").read_text())
    for case in cases["oklch"]:
        assert hex_to_oklch(case["hex"]) == pytest.approx(case["oklch"], abs=1e-6)
    for case in cases["simulate"]:
        assert simulate(case["hex"], case["kind"]) == case["result"]
    for case in cases["delta_e"]:
        assert delta_e(case["a"], case["b"], case["kind"]) == pytest.approx(case["value"], abs=1e-6)
    for case in cases["contrast"]:
        assert contrast(case["a"], case["b"]) == pytest.approx(case["value"], abs=1e-6)
