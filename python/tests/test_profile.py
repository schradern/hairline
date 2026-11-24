import warnings

import numpy as np
import pandas as pd
import pytest

import hairline as hl
from hairline.interactive import figure_targets
from hairline.stats.histogram import histogram, round_width


def operations(count=120):
    """One surgical cohort: numbers, categories, a missing weight and operation dates as ISO text."""
    generator = np.random.default_rng(3)
    weight = np.round(generator.normal(80, 14, count), 1)
    weight[4] = np.nan
    days = pd.Timestamp("2023-01-02") + pd.to_timedelta(generator.integers(0, 700, count), unit="D")
    return pd.DataFrame({"id": range(1, count + 1), "sex": generator.choice(["Female", "Male"], count),
                         "age": np.round(generator.normal(60, 12, count)), "weight": weight,
                         "asa": generator.choice(["ASA I", "ASA II", "ASA III"], count),
                         "stay": 1 + generator.poisson(4, count), "arm": generator.choice(["A", "B"], count),
                         "surgery_date": days.strftime("%Y-%m-%d")})


def cohort_study(data=None, **options):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return hl.study(operations() if data is None else data, id="id",
                        variables=options.pop("variables", ["age", "sex", "weight", "asa", "stay"]),
                        labels={"asa": "ASA class", "stay": "Length of stay"},
                        units={"age": "years", "weight": "kg", "stay": "days"}, unit="patients", **options)


def test_profile_is_table_one_of_the_whole_cohort_with_a_tile_per_variable():
    result = cohort_study().profile(dates="surgery_date")
    assert list(result.table.columns) == ["Characteristic", "Overall"]
    assert result.table.iloc[0].tolist() == ["n", "120"]
    assert result.table.iloc[-1, 0] == "Surgery date, first to last"
    assert result.values["weight"]["Overall"] == result.table.set_index("Characteristic").loc[
        "Weight (kg), median (IQR)", "Overall"]
    assert result.text == "120 patients. Missing: Weight 1."
    assert len(result.figure.axes) == 6 and result.figure.columns == 3
    assert [header.name for header in result.figure.headers.values()] == [
        "Age", "Sex", "Weight", "ASA class", "Length of stay", "Surgery date"]
    assert result.figure.headers[2].qualifier == "1 missing"
    assert result.figure.headers[5].qualifier == "per month"


def test_profile_describes_every_row_whatever_the_group():
    result = cohort_study(group="arm").profile()
    assert list(result.table.columns) == ["Characteristic", "Overall"]
    assert result.numbers["n"] == 120


def test_profile_lays_out_without_collisions_and_tips_every_tile():
    result = cohort_study().profile(dates=["surgery_date"])
    assert hl.check_layout(result.figure) == []
    series = figure_targets(result.figure)["series"]
    assert [entry["name"] for entry in series] == ["Age", "Sex", "Weight", "ASA class", "Length of stay",
                                                   "Surgery date"]
    assert all(entry["tips"] for entry in series)
    stay = next(entry for entry in series if entry["name"] == "Length of stay")
    assert stay["tips"][0]["text"].startswith("Length of stay 1 days: ")


@pytest.mark.parametrize(("size", "columns"), [("single", 1), ("onehalf", 2), ("double", 3)])
def test_profile_tiles_follow_the_width(size, columns):
    assert cohort_study().profile(size=size).figure.columns == columns


def test_profile_refuses_dates_it_cannot_read():
    data = operations().assign(surgery_date=lambda frame: frame["surgery_date"].where(frame.index != 3, "soon"))
    with pytest.raises(ValueError, match="'surgery_date' has 'soon', which is not a date"):
        cohort_study(data).profile(dates="surgery_date")
    with pytest.raises(ValueError, match="date column 'operated' is not in the data"):
        cohort_study().profile(dates="operated")


def test_profile_counts_by_quarter_over_long_periods():
    data = operations().assign(surgery_date=pd.date_range("2015-01-01", periods=120, freq="MS"))
    result = cohort_study(data).profile(dates="surgery_date")
    assert result.figure.headers[5].qualifier == "per quarter"


def test_profile_without_variables_has_no_figure():
    result = cohort_study(variables=[]).profile()
    assert result.figure is None and result.table.iloc[0].tolist() == ["n", "120"]


def test_round_widths_are_nearest_on_a_log_scale_and_whole_for_whole_numbers():
    assert round_width(5.4, whole=True) == 5
    assert round_width(3.4, whole=False) == 2.5
    assert round_width(2.8, whole=True) == 2
    assert round_width(0.3, whole=True) == 1


def test_histogram_bins_hold_every_value_once():
    values = np.random.default_rng(1).normal(50, 10, 500)
    lefts, counts, width = histogram(values, whole=False)
    assert sum(counts) == 500 and lefts[0] <= values.min() < lefts[-1] + width
    days = [1, 1, 2, 4, 4, 4, 9]
    lefts, counts, width = histogram(days, whole=True)
    assert width == 1 and lefts[0] == 0.5 and counts[0] == 2 and sum(counts) == len(days)


def test_profile_by_a_column_splits_every_tile_in_the_session_colours():
    result = cohort_study().profile(dates="surgery_date", by="sex")
    assert list(result.table.columns) == ["Characteristic", "Female", "Male", "Overall"]
    females = int((operations()["sex"] == "Female").sum())
    assert result.text.startswith(f"120 patients; by sex, {females} Female and {120 - females} Male.")
    assert [item.label for item in result.figure.legend_items] == ["Female", "Male"]
    assert result.figure.legend_heading == "Sex"
    series = {entry["name"]: entry for entry in figure_targets(result.figure)["series"]}
    assert set(series) == {"Female", "Male"}
    assert any(", Female: " in tip["text"] for tip in series["Female"]["tips"])
    assert hl.check_layout(result.figure) == []


def test_profile_by_keeps_rows_without_a_group_as_missing_in_grey():
    data = operations().assign(sex=lambda frame: frame["sex"].where(frame.index >= 3))
    result = cohort_study(data).profile(by="sex")
    assert [item.label for item in result.figure.legend_items][-1] == "Missing"
    assert result.text.split(". ")[1] == "3 without a sex are in Overall only"
    assert result.table.iloc[0, -1] == "120"


def test_profile_by_refuses_numbers_and_unknown_columns():
    with pytest.raises(ValueError, match="by 'age' holds numbers"):
        cohort_study().profile(by="age")
    with pytest.raises(ValueError, match="by 'ward' is not a column"):
        cohort_study().profile(by="ward")
