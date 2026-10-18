import json

import pytest

from hairline.numbers import format_interval, format_number, format_percent


def test_thousands_and_decimals():
    assert format_number(2184, 0, "en") == "2,184"
    assert format_number(2184, 0, "de") == "2 184"
    assert format_number(1234567.891, 2, "de") == "1 234 567,89"
    assert format_number(0.5, 1, "de") == "0,5"


def test_true_minus_sign():
    assert format_number(-0.5, 1, "en") == "−0.5"
    assert format_number(-0.04, 1, "en") == "0.0"


def test_percent():
    assert format_percent(0.614, 1, "de") == "61,4 %"
    assert format_percent(0.614, 1, "en") == "61.4%"
    assert format_percent(1.04, 0, "en") == "104%"


def test_interval():
    assert format_interval(0.58, 0.41, 0.82, 2, "de") == "0,58 [0,41; 0,82]"
    assert format_interval(0.58, 0.41, 0.82, 2, "en") == "0.58 [0.41; 0.82]"


def test_unknown_locale():
    with pytest.raises(ValueError, match="unknown locale 'fr'.*de, en"):
        format_number(1, 0, "fr")


def test_fixture_cases(repo_root):
    for case in json.loads((repo_root / "tokens/fixtures/numbers.json").read_text()):
        function = {"number": format_number, "percent": format_percent}[case["kind"]]
        assert function(case["value"], case["digits"], case["locale"]) == case["result"]


@pytest.mark.parametrize(("value", "digits", "expected"), [
    (8.65, 1, "8.7"), (8.649999999999999, 1, "8.7"), (2.45, 1, "2.5"), (0.125, 2, "0.13"), (0.25, 1, "0.3"),
    (-2.45, 1, "−2.5"), (2.5, 0, "3"), (0.5, 0, "1"), (1234.5, 0, "1,235"), (8.6449, 1, "8.6"), (0.0, 2, "0.00"),
    (-0.04, 1, "0.0"), (1e-7, 3, "0.000"),
])
def test_halves_round_up_on_every_platform(value, digits, expected):
    """A value at the half rounds away from zero, whatever its binary representation; float noise does not decide."""
    assert format_number(value, digits) == expected
