import json

import pytest

from hairline.ticks import nice_breaks


def test_known_ranges():
    assert nice_breaks(0, 100) == [0, 25, 50, 75, 100]
    assert nice_breaks(0.21, 0.88) == [0, 0.25, 0.5, 0.75, 1.0]
    assert nice_breaks(40, 45, target=3) == [40, 42.5, 45]
    assert nice_breaks(3, 3) == [2, 2.5, 3, 3.5, 4]


@pytest.mark.parametrize("low, high", [(0, 1), (-7, 13), (1e-3, 9e-3), (0, 546), (0, 0), (-1, -1), (99, 101)])
def test_three_to_six_breaks_nearly_covering_range(low, high):
    breaks = nice_breaks(low, high)
    extent = breaks[-1] - breaks[0]
    assert 3 <= len(breaks) <= 6
    assert breaks[0] - low <= 0.1 * extent + 1e-12 and high - breaks[-1] <= 0.2 * extent + 1e-12


def test_small_overshoot_does_not_add_a_tick():
    assert nice_breaks(0.45, 1.07, target=3) == [0, 0.5, 1.0]
    assert nice_breaks(-0.04, 0.88, target=3) == [0, 0.5, 1.0]


def test_occupancy_above_full_does_not_double_the_axis():
    assert nice_breaks(0.2, 1.2, target=3) == [0, 0.5, 1.0]
    assert nice_breaks(0, 8) == [0, 2, 4, 6, 8]
    assert nice_breaks(-0.3, 0.3) == [-0.4, -0.2, 0, 0.2, 0.4]


def test_month_breaks_and_labels():
    import datetime as dt

    from hairline.ticks import month_breaks, month_label
    breaks = month_breaks(dt.date(2025, 1, 1), dt.date(2026, 6, 30))
    assert breaks == [dt.date(2025, 1, 1), dt.date(2025, 5, 1), dt.date(2025, 9, 1), dt.date(2026, 1, 1),
                      dt.date(2026, 5, 1)]
    assert [month_label(day, "en") for day in breaks[:3]] == ["2025", "May", "Sep"]
    assert month_label(dt.date(2025, 3, 1), "de") == "Mär"
    assert month_breaks(dt.date(2025, 1, 10), dt.date(2025, 3, 20)) == [dt.date(2025, 2, 1), dt.date(2025, 3, 1)]


def test_axis_limits_cover_data_and_breaks():
    from hairline.ticks import axis_limits
    assert axis_limits(0.45, 1.07, [0, 0.5, 1.0]) == (0, 1.07)
    assert axis_limits(0.21, 0.88, [0.2, 0.4, 0.6, 0.8, 1.0]) == (0.2, 1.0)


def test_reversed_input_is_rejected():
    with pytest.raises(ValueError, match="low 5 is above high 1"):
        nice_breaks(5, 1)


def test_fixture_cases(repo_root):
    for case in json.loads((repo_root / "tokens/fixtures/breaks.json").read_text()):
        assert nice_breaks(case["low"], case["high"]) == pytest.approx(case["breaks"], abs=1e-12)
