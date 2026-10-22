import json

import pytest

import hairline as hl
from hairline.fonts import face_weight, family_weights, nearest_weight
from hairline.layout.styles import role_style
from hairline.settings import current_settings
from hairline.tokens import load_tokens


def test_nearest_weight_matches_the_shared_fixture(repo_root):
    for case in json.loads((repo_root / "tokens/fixtures/weights.json").read_text()):
        assert nearest_weight(case["requested"], case["available"]) == case["result"], case


@pytest.mark.parametrize(("requested", "available", "expected"), [
    (600, [400, 700], 700),        # semibold of a family with regular and bold: its bold, as browsers draw it
    (500, [400, 700], 400),        # medium falls back to regular before bold
    (600, [400, 500], 500),        # nothing heavier: the nearest lighter face
    (300, [400, 700], 400),        # nothing lighter: the nearest heavier face
    (450, [400, 500, 700], 500),   # between 400 and 500: up to 500 first
    (600, [], 600),                # an unknown family keeps the request
])
def test_nearest_weight_follows_css_font_matching(requested, available, expected):
    assert nearest_weight(requested, available) == expected


def test_the_bundled_family_has_its_semibold():
    family = load_tokens()["font"]["family"]
    assert family_weights(family) == [400, 500, 600]
    assert face_weight(family, 600) == 600


def test_role_styles_carry_a_weight_the_family_has():
    hl.use(brand=False, font="DejaVu Sans")
    settings = current_settings()
    assert role_style(settings, "title")["weight"] == 700
    assert role_style(settings, "label")["weight"] == 400
    assert role_style(settings, "label", 600)["weight"] == 700
