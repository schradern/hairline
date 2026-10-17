import pytest

from hairline.numbers import format_p
from hairline.stats.distributions import chi2_sf, normal_cdf, t_cdf, t_quantile
from hairline.stats.tests import egger, linear_fit, logrank, pearson, rank_sum

R = 1e-9


def test_distributions_match_r():
    assert chi2_sf(3.84, 1) == pytest.approx(0.050043521248705, abs=R)
    assert chi2_sf(7.2, 3) == pytest.approx(0.065789052685071, abs=R)
    assert chi2_sf(0.5, 2) == pytest.approx(0.778800783071405, abs=R)
    assert t_cdf(2.1, 10) == pytest.approx(0.968961377898891, abs=R)
    assert t_cdf(-1.3, 4) == pytest.approx(0.131725798235612, abs=R)
    assert t_quantile(0.975, 10) == pytest.approx(2.22813885198627, abs=1e-8)
    assert t_quantile(0.975, 3) == pytest.approx(3.18244630528371, abs=1e-8)
    assert normal_cdf(-1.96) == pytest.approx(0.0249978951482204, abs=R)


def test_rank_sum_matches_wilcox_test():
    x = [1.2, 3.4, 2.2, 5.1, 4.4, 3.3, 2.0]
    y = [2.1, 2.9, 4.4, 6.0, 5.5, 5.1, 3.3, 7.0]
    assert rank_sum(x, y) == pytest.approx(0.131425654489038, abs=R)


def test_logrank_matches_survdiff():
    time = [1, 2, 2, 3, 4, 5, 6, 6, 7, 8]
    event = [1, 1, 0, 1, 1, 0, 1, 1, 0, 1]
    group = ["a", "b"] * 5
    result = logrank(time, event, group)
    assert result["chisq"] == pytest.approx(0.0121684570776689, abs=R)
    assert result["p"] == pytest.approx(0.912162948160635, abs=R)


def test_linear_fit_and_correlation_match_r():
    x, y = [1, 2, 3, 4, 5, 6], [1.1, 1.9, 3.2, 3.8, 5.3, 5.9]
    fit = linear_fit(x, y)
    assert fit["intercept"] == pytest.approx(0.0533333333333325, abs=R)
    assert fit["slope"] == pytest.approx(0.994285714285714, abs=R)
    assert fit["slope_se"] == pytest.approx(0.0524761040531654, abs=R)
    r, p = pearson(x, y)
    assert r == pytest.approx(0.994475156168787, abs=R) and p == pytest.approx(4.57015291503983e-05, rel=1e-6)


def test_egger_detects_asymmetry():
    estimate = [0.2, 0.35, 0.5, 0.9, 1.3]
    se = [0.05, 0.1, 0.2, 0.35, 0.5]
    assert egger(estimate, se) < 0.05


def test_p_values_are_formatted_for_reading():
    assert format_p(0.0004) == "p < 0.001"
    assert format_p(0.0123) == "p = 0.012"
    assert format_p(0.5) == "p = 0.50"
    assert format_p(0.0123, "de") == "p = 0,012"
