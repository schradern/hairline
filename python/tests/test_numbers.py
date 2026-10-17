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
