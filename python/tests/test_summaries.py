"""summary= and stats=: one vocabulary of measures, drawn and written the same way on every distribution chart (the R
package checks the same in test-summaries.R)."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import hairline as hl
from hairline.charts.summaries import check_paired, check_summary, stat_pairs, summary_values
from hairline.charts.timeseries import panel_stats
from hairline.errors import HairlineLayoutError


@pytest.fixture(autouse=True)
def plain():
    hl.use(brand=False)
    yield
    plt.close("all")


def stays(groups: int = 3, size: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    names = [f"Unit {letter}" for letter in "ABCDEFGH"[:groups]]
    return pd.DataFrame({"unit": np.repeat(names, size), "days": np.round(rng.lognormal(1.8, 0.4, groups * size), 1)})


def legend_labels(figure) -> list[str]:
    figure.figure.canvas.draw()
    return figure.layout_report()["legend_labels"]


def test_measures_match_their_definitions():
    found = summary_values(np.arange(1.0, 11.0))
    assert (found["median"], found["q1"], found["q3"], found["mean"]) == (5.5, 3.25, 7.75, 5.5)
    assert found["sd"] == pytest.approx(3.0276504)
    # mean ± t(0.975, 9) · sd / √n, as R's t.test() gives
    assert (found["ci_low"], found["ci_high"]) == pytest.approx((3.3341494, 7.6658506))
    assert np.isnan(summary_values([4.0])["sd"])


def test_numbers_are_named_in_the_locale():
    numbers = (lambda value: f"{value:.1f}", lambda value: f"{value:.2f}")
    pairs = stat_pairs(np.arange(1.0, 11.0), ["median", "iqr", "sd", "ci", "n"], numbers)
    assert pairs == [["Median", "5.5"], ["IQR", "3.2–7.8"], ["SD", "3.03"], ["95% CI", "3.33–7.67"], ["n", "10"]]
    hl.use(brand=False, locale="de")
    assert [label for label, _ in stat_pairs([1.0, 2.0], ["range", "ci"], numbers)] == ["Spannweite", "95 %-KI"]


def test_summaries_are_checked_before_drawing():
    with pytest.raises(ValueError, match="unknown summary 'average'"):
        check_summary(["mean", "average"], "raincloud")
    with pytest.raises(ValueError, match="'iqr' and 'ci' would draw two bars in one place"):
        check_summary(["median", "iqr", "ci"], "raincloud")
    with pytest.raises(ValueError, match="names 'mean' twice"):
        check_summary(["mean", "mean"], "spread")
    with pytest.raises(ValueError, match="'ci' goes with the mean"):
        check_paired(("median", "ci"), "dotplot")
    with pytest.raises(ValueError, match="needs one centre"):
        check_paired(("iqr",), "timeseries")
    assert check_paired(("mean", "range"), "dotplot") == ("mean", "range")


def test_raincloud_draws_the_summary_named_in_the_legend_and_its_numbers_under_the_groups():
    figure = hl.raincloud(stays(), "unit", "days", summary=("mean", "ci", "range"), stats=("mean", "ci"),
                          size="single")
    assert legend_labels(figure) == ["Mean", "95% CI", "Range"]
    assert [label for label, _, _ in figure.table_spec["rows"]] == ["", "Mean", "95% CI"]
    assert hl.check_layout(figure) == []
    default = hl.raincloud(stays(), "unit", "days")
    assert legend_labels(default) == []
    with pytest.raises(ValueError, match="use spread\\(facet=...\\)"):
        hl.raincloud(stays().assign(site="North"), "unit", "days", stats="mean", facet="site")


def test_raincloud_counts_shorten_before_they_meet_and_numbers_that_cannot_stand_apart_stop_the_figure():
    figure = hl.raincloud(stays(8, 20), "unit", "days", size="single")
    figure.figure.canvas.draw()
    assert figure.table_spec["compact"][0][0] == "n"
    assert hl.check_layout(figure) == []
    figure = hl.raincloud(stays(8, 20), "unit", "days", stats=("iqr", "ci"), size="single")
    with pytest.raises(HairlineLayoutError, match="do not fit side by side.*use a wider size"):
        figure.figure.canvas.draw()


def test_spread_draws_a_slim_bar_for_the_ci_and_writes_sd_and_ci():
    from hairline.charts.spread import spread_spec
    spec = spread_spec(stays(), "unit", "days", summary=("mean", "ci"), stats=("mean", "sd", "ci"))
    row = spec["rows"][0]
    assert row["bar"][2] is True and not row["range"] and not row["show_median"]
    assert [label for label, _ in row["pairs"]] == ["Mean", "SD", "95% CI"]
    assert [label for _, _, label in spec["legend"]] == ["Mean", "95% CI"]
    assert hl.check_layout(hl.spread(stays(), "unit", "days", summary=("mean", "ci"), size="single")) == []


def test_ridgeline_marks_centres_and_writes_numbers_beside_each_ridge():
    figure = hl.ridgeline(stays(4), "unit", "days", summary=("median", "mean"), stats=("median", "n"),
                          size="single")
    assert len(figure.side_numbers[0]) == 8
    assert legend_labels(figure) == ["Median", "Mean"]
    assert hl.check_layout(figure) == []
    with pytest.raises(ValueError, match="A ridge shows its own spread"):
        hl.ridgeline(stays(), "unit", "days", summary=("median", "iqr"))


def test_dotplot_summarises_rows_per_label():
    figure = hl.dotplot(stays(), "unit", "days", summary=("mean", "ci"), size="single")
    assert hl.check_layout(figure) == []
    with pytest.raises(ValueError, match="leave out low, high and n"):
        hl.dotplot(stays().assign(low=1.0), "unit", "days", low="low", high="low", summary="mean")
    single = pd.DataFrame({"unit": ["A", "A", "B"], "days": [1.0, 2.0, 3.0]})
    with pytest.raises(ValueError, match="'B' has one value, and an SD needs two or more"):
        hl.dotplot(single, "unit", "days", summary=("mean", "sd"))


def test_timeseries_summarises_each_x_and_names_line_and_band():
    days = pd.date_range("2025-01-01", periods=20)
    data = pd.DataFrame({"day": np.repeat(days, 5), "score": np.arange(100.0) % 17})
    figure = hl.timeseries(data, "day", "score", summary=("mean", "ci"), stats=("mean", "sd", "n"), size="single")
    assert legend_labels(figure) == ["Mean", "95% CI"]
    assert [label for label, _ in figure.headers[0].stats] == ["Mean", "SD", "n"]
    assert hl.check_layout(figure) == []
    assert panel_stats(pd.Series([np.nan]), ["median", "n"], False, None, "") == [("Median", "–"), ("n", "–")]
