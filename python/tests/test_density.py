import numpy as np
import pytest

from hairline.stats.density import bandwidth, density, jitter_offsets, quantiles


def test_bandwidth_follows_silverman():
    values = np.array([1.0, 2.0, 3.0, 4.0, 10.0])
    spread = min(values.std(ddof=1), (np.quantile(values, 0.75) - np.quantile(values, 0.25)) / 1.34)
    assert bandwidth(values) == pytest.approx(0.9 * spread * len(values) ** -0.2)


def test_density_integrates_to_about_one_over_the_data_range():
    values = np.linspace(0, 10, 200)
    grid, height = density(values)
    assert grid[0] == 0 and grid[-1] == 10 and len(grid) == 128
    assert np.trapezoid(height, grid) == pytest.approx(1, abs=0.1)


def test_single_value_has_no_density():
    assert density([4.0]) is None
    assert density([4.0, 4.0, 4.0]) is None


def test_quantiles_use_type_seven():
    assert quantiles([1, 2, 3, 4], [0.25, 0.5, 0.75]) == pytest.approx([1.75, 2.5, 3.25])


def test_jitter_is_deterministic_and_within_half():
    offsets = jitter_offsets(50)
    assert offsets == jitter_offsets(50)
    assert all(-0.5 <= value <= 0.5 for value in offsets)
    assert offsets[0] == pytest.approx(0.618034 - 0.5)
