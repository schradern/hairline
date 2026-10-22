import warnings

import numpy as np
import pandas as pd
import pytest

import hairline as hl


def cohort():
    """Two arms; messy on purpose: a spelling variant, a missing age, a duplicate id, numbers stored as text."""
    generator = np.random.default_rng(7)
    count = 40
    arms = ["Standard care"] * (count // 2) + ["Early mobilisation"] * (count // 2)
    sex = list(generator.choice(["Female", "Male"], count))
    sex[3] = "female "
    age = np.round(generator.normal(64, 10, count)).astype(float)
    age[5] = np.nan
    return pd.DataFrame({"id": list(range(1, count)) + [1], "arm": arms, "sex": sex, "age": age,
                         "sofa": np.round(generator.gamma(3, 2, count), 1),
                         "score": [str(value) for value in generator.integers(0, 9, count)],
                         "months": np.round(generator.exponential(12, count), 1),
                         "died": generator.integers(0, 2, count)})


def quiet(**roles):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return hl.study(cohort(), **roles)


def test_checks_report_without_changing_the_data():
    data = cohort()
    with pytest.warns(UserWarning, match="0 errors, 5 warnings"):
        study = hl.study(data, group="arm", time="months", event="died", id="id",
                         variables=["age", "sex", "sofa", "score"], units={"age": "years", "months": "months"})
    problems = [(finding.column, finding.problem) for finding in study.checks]
    assert ("id", "1 row repeats an id") in problems
    assert ("age", "1 missing (2.5%)") in problems
    assert any(column == "sex" and "'female '" in problem for column, problem in problems)
    assert any(column == "score" and problem.startswith("stored as text") for column, problem in problems)
    assert ("sofa", "numeric columns without a unit") in problems
    assert data.equals(cohort())


def test_errors_block_only_the_endpoints_that_need_the_column():
    data = cohort().assign(died=["yes"] + [0] * 39)
    with pytest.warns(UserWarning):
        study = hl.study(data, group="arm", time="months", event="died", variables=["age"])
    assert study.checks[0].level == "error" and study.checks[0].rows == (1,)
    with pytest.raises(ValueError, match="survival: fix these first"):
        study.survival()
    assert study.describe().table.iloc[0, 0] == "n"


def test_describe_builds_table_one_with_counts_and_shares():
    study = quiet(group="arm", variables=["age", "sex"], units={"age": "years"})
    result = study.describe()
    assert list(result.table.columns) == ["Characteristic", "Standard care", "Early mobilisation", "Overall"]
    assert result.table.iloc[0].tolist() == ["n", "20", "20", "40"]
    assert result.table.iloc[1, 0] == "Age (years), median (IQR)"
    assert result.figure.headers[0].x_title == "years"
    assert result.values["n"]["Overall"] == "40"
    assert result.text == ("40 participants: 20 in Standard care and 20 in Early mobilisation. Left out where missing: "
                           "Age 1.")
    assert result.table.iloc[2, 0] == "Sex, n (%)"
    assert result.figure is not None and len(result.figure.axes) == 1


def test_compare_numeric_two_groups_uses_rank_sum_everywhere():
    result = quiet(group="arm").compare("sofa")
    assert result.values["test"] == "Wilcoxon rank-sum"
    assert result.values["p"] in result.text and result.values["p"] in result.table.iloc[-1, 2]


def test_compare_categorical_uses_chi_squared():
    result = quiet(group="arm").compare("sex")
    assert result.values["test"] == "Chi-squared"
    assert result.table.columns[0] == "Sex"


def test_survival_and_effects():
    study = quiet(group="arm", time="months", event="died")
    survival = study.survival()
    assert list(survival.table.columns) == ["Group", "n", "Events", "Median"] and "log-rank" in survival.text
    table = pd.DataFrame({"study": ["age", "sofa"], "estimate": [1.2, 1.8], "low": [1.0, 1.2], "high": [1.5, 2.6]})
    effects = study.effects(table, measure="OR")
    assert effects.values["Age"] == "OR 1.20 [1.00; 1.50]"
    assert effects.text.startswith("Age OR 1.20")


def test_kruskal_and_chi_square_match_r():
    from hairline.stats.tests import chi_square, kruskal
    assert kruskal([[1, 2, 3, 4], [2, 5, 6, 7], [8, 9, 9, 10]]) == pytest.approx(0.01351253746, abs=1e-9)
    assert chi_square([[10, 20], [30, 25]]) == pytest.approx(0.06115089758, abs=1e-9)


def daily():
    generator = np.random.default_rng(5)
    dates = pd.date_range("2025-01-01", periods=60).strftime("%Y-%m-%d").tolist()
    return pd.DataFrame({"date": dates * 2, "unit": ["North"] * 60 + ["South"] * 60,
                         "occupied": generator.integers(4, 14, 120)})


def test_over_time_reads_iso_dates_and_reports_means_per_group():
    study = quiet_study(daily(), group="unit", variables=["occupied"], units={"occupied": "beds"})
    result = study.over_time("date", "occupied")
    assert list(result.table.columns) == ["Group", "n", "mean (SD)", "median (IQR)"]
    assert result.table.iloc[0, 1] == "60"
    assert result.text.startswith("Occupied (beds), mean over the period: North ")
    assert len(result.figure.axes) == 2
    with pytest.raises(ValueError, match="not an ISO date"):
        quiet_study(daily().assign(date="next week"), group="unit", variables=["occupied"]).over_time(
            "date", "occupied")


def test_survival_from_a_lifelines_fit_matches_the_raw_rows():
    lifelines = pytest.importorskip("lifelines")
    data = cohort()
    study = quiet(group="arm", time="months", event="died", units={"months": "months"})
    fits = {name: lifelines.KaplanMeierFitter().fit(rows["months"], rows["died"], label=name)
            for name, rows in data.groupby("arm", sort=False)}
    from_fit, from_rows = study.survival(fit=fits), study.survival()
    assert from_fit.table.equals(from_rows.table)
    assert from_fit.values == from_rows.values and from_fit.text == from_rows.text


def quiet_study(data, **roles):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return hl.study(data, **roles)
