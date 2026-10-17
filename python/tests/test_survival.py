import math

import numpy as np
import pytest

from hairline.stats.survival import km_estimate, km_median


def test_product_limit_with_ties_and_censoring():
    table = km_estimate([1, 2, 2, 3, 4, 5], [1, 1, 0, 1, 0, 1])
    assert list(table["time"]) == [1, 2, 3, 4, 5]
    assert list(table["at_risk"]) == [6, 5, 3, 2, 1]
    expected = np.cumprod([5 / 6, 4 / 5, 2 / 3, 1, 0])
    assert table["survival"].to_numpy() == pytest.approx(expected)


def test_greenwood_band_on_the_log_scale():
    table = km_estimate([1, 2, 3, 4], [1, 0, 1, 0])
    variance = 1 / (4 * 3)
    first = table.iloc[0]
    assert first["low"] == pytest.approx(0.75 * math.exp(-1.959963984540054 * math.sqrt(variance)))
    assert first["high"] == pytest.approx(min(1.0, 0.75 * math.exp(1.959963984540054 * math.sqrt(variance))))


def test_band_is_missing_once_survival_reaches_zero():
    table = km_estimate([1, 2], [1, 1])
    assert math.isnan(table.iloc[-1]["low"]) and math.isnan(table.iloc[-1]["high"])


def test_censoring_at_time_zero_counts_as_at_risk():
    table = km_estimate([0, 1, 2], [0, 1, 1])
    assert list(table["at_risk"]) == [3, 2, 1]
    assert table["survival"].iloc[0] == 1


def test_median_or_not_reached():
    assert km_median(km_estimate([1, 2, 3, 4], [1, 1, 1, 1])) == 2
    assert km_median(km_estimate([1, 2, 3, 4], [1, 0, 0, 0])) is None


def test_event_must_be_zero_or_one():
    with pytest.raises(ValueError, match="event values must be 0 or 1; found 2"):
        km_estimate([1, 2], [1, 2])


def test_times_must_not_be_negative():
    with pytest.raises(ValueError, match="time -1 is negative"):
        km_estimate([-1, 2], [1, 1])
