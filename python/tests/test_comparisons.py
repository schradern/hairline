"""compare= and numbers=: differences with their CI and p beside the other numbers, the test named in the caption,
and the numbers placed beside or under the rows (the R package checks the same in test-comparisons.R)."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import hairline as hl
from hairline.charts.comparisons import check_compare, shift, welch
from hairline.charts.spread import spread_spec
from hairline.errors import HairlineLayoutError


@pytest.fixture(autouse=True)
def plain():
    hl.use(brand=False)
    yield
    plt.close("all")


def units() -> pd.DataFrame:
    rng = np.random.default_rng(1)
    return pd.DataFrame({"unit": np.repeat(["Unit A", "Unit B", "Unit C"], 40),
                         "days": np.round(rng.lognormal(2, 0.4, 120) + np.repeat([0, 1, 3], 40), 1)})


def test_welch_matches_t_test_and_the_shift_its_rank_interval():
    found = welch(np.array([1.0, 2, 3, 4, 5]), np.array([2.0, 4, 6, 8, 10]))
    # R: t.test(c(1:5), c(2, 4, 6, 8, 10))
    assert (found["estimate"], found["low"], found["high"], found["p"]) == pytest.approx(
        (-3.0, -6.8877416, 0.8877416, 0.1075312))
    found = shift(np.array([4.1, 5.3, 6.0, 6.2, 7.7, 8.4, 9.1, 10.5]), np.array([2.2, 3.1, 3.9, 4.4, 5.0, 5.8, 6.6]))
    # R: wilcox.test(..., conf.int = TRUE) gives the same shift and interval here
    assert (found["estimate"], found["low"], found["high"]) == pytest.approx((2.65, 0.3, 5.2))
    assert found["p"] == pytest.approx(0.0240277, abs=1e-7)


def test_compare_names_a_group_or_adjacent():
    assert check_compare(None, ["A"], "spread") is None
    with pytest.raises(ValueError, match="compare='all' would need a number for every pair"):
        check_compare("all", ["A", "B"], "spread")
    with pytest.raises(ValueError, match="compare names 'D', which is not a group"):
        check_compare("D", ["A", "B"], "spread")


def test_spread_writes_differences_and_names_the_test_that_follows_the_centre():
    spec = spread_spec(units(), "unit", "days", compare="Unit A")
    assert [row["pairs"][-2] for row in spec["rows"]] == [["Δ", "Reference"], ["Δ", "0.6 [−0.5; 1.6]"],
                                                          ["Δ", "3.1 [2.0; 4.1]"]]
    assert spec["notes"][-1].startswith("Δ: Hodges–Lehmann shift against Unit A")
    assert spec["notes"][-1].endswith("Not adjusted for multiple comparisons.")
    spec = spread_spec(units(), "unit", "days", compare="adjacent", summary=("mean", "ci"))
    assert [row["pairs"][-1] for row in spec["rows"]] == [["p", "–"], ["p", "0.53"], ["p", "< 0.001"]]
    assert "Welch's t-test" in spec["notes"][-1]


def test_comparisons_on_raincloud_ridgeline_and_dotplot_stay_clear():
    figures = [hl.raincloud(units(), "unit", "days", compare="adjacent", size="single"),
               hl.ridgeline(units(), "unit", "days", compare="Unit A", stats="median", size="onehalf"),
               hl.dotplot(units(), "unit", "days", summary=("mean", "ci"), compare="Unit A", size="onehalf")]
    for figure in figures:
        assert hl.check_layout(figure) == []
    assert [label for label, _, _ in figures[0].table_spec["rows"]] == ["", "Δ", "p"]
    with pytest.raises(ValueError, match="compare needs summary="):
        hl.dotplot(units(), "unit", "days", compare="Unit A")
    with pytest.raises(ValueError, match="facet panels do not have"):
        hl.raincloud(units().assign(site="North"), "unit", "days", compare="Unit A", facet="site")


def test_numbers_go_beside_or_under_the_rows_as_asked():
    for place in ("auto", "right", "below"):
        figure = hl.spread(units(), "unit", "days", compare="Unit A", stats=("median", "n"), numbers=place,
                           size="onehalf")
        assert hl.check_layout(figure) == []
    with pytest.raises(ValueError, match="numbers 'left' must be one of"):
        hl.spread(units(), "unit", "days", numbers="left")
    with pytest.raises(HairlineLayoutError, match="numbers beside the plot leave it.*use a wider size"):
        hl.spread(units(), "unit", "days", compare="Unit A", stats=("median", "iqr", "mean", "n"), numbers="right",
                  size="single")
    assert hl.check_layout(hl.dotplot(units(), "unit", "days", summary=("mean", "ci"), numbers="below",
                                      size="onehalf")) == []
