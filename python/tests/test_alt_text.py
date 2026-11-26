import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import hairline as hl
from hairline.alt_text import extremes, grid_extremes
from hairline.export import figure_alt

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "alt_text.json").read_text(encoding="utf-8"))


def frame_of(case):
    return pd.DataFrame({key: [np.nan if value is None else value for value in values]
                         for key, values in case["data"].items()})


def case_id(case):
    return f"{case['locale']}-{sorted(case['options'])}"


@pytest.mark.parametrize("case", FIXTURE["bars"], ids=case_id)
def test_bar_alt_text_matches_the_shared_fixture(case):
    hl.use(brand=False, locale=case["locale"])
    assert figure_alt(hl.bars(frame_of(case), "unit", "n", **case["options"])) == case["alt"]
    hl.use(brand=False)


@pytest.mark.parametrize("case", FIXTURE["timeseries"], ids=case_id)
def test_time_series_alt_text_matches_the_shared_fixture(case):
    hl.use(brand=False, locale=case["locale"])
    assert figure_alt(hl.timeseries(frame_of(case), "t", "v", **case["options"])) == case["alt"]
    hl.use(brand=False)


@pytest.mark.parametrize("case", FIXTURE["distributions"], ids=lambda case: f"{case['chart']}-{case_id(case)}")
def test_distribution_alt_text_matches_the_shared_fixture(case):
    hl.use(brand=False, locale=case["locale"])
    draw = {"spread": hl.spread, "raincloud": hl.raincloud, "ridgeline": hl.ridgeline}[case["chart"]]
    assert figure_alt(draw(frame_of(case), "unit", "days", **case["options"])) == case["alt"]
    hl.use(brand=False)


@pytest.mark.parametrize("case", FIXTURE["kaplan_meier"], ids=case_id)
def test_kaplan_meier_alt_text_matches_the_shared_fixture(case):
    hl.use(brand=False, locale=case["locale"])
    assert figure_alt(hl.kaplan_meier(frame_of(case), "t", "e", **case["options"])) == case["alt"]
    hl.use(brand=False)


@pytest.mark.parametrize("case", FIXTURE["forest"], ids=case_id)
def test_forest_alt_text_matches_the_shared_fixture(case):
    hl.use(brand=False, locale=case["locale"])
    assert figure_alt(hl.forest(frame_of(case), **case["options"])) == case["alt"]
    hl.use(brand=False)


@pytest.mark.parametrize("case", FIXTURE["dotplot"], ids=case_id)
def test_dot_plot_alt_text_matches_the_shared_fixture(case):
    hl.use(brand=False, locale=case["locale"])
    assert figure_alt(hl.dotplot(frame_of(case), **case["options"])) == case["alt"]
    hl.use(brand=False)


@pytest.mark.parametrize("case", FIXTURE["scatter"], ids=case_id)
def test_scatter_alt_text_matches_the_shared_fixture(case):
    hl.use(brand=False, locale=case["locale"])
    assert figure_alt(hl.scatter(frame_of(case), "x", "y", **case["options"])) == case["alt"]
    hl.use(brand=False)

@pytest.mark.parametrize("case", FIXTURE["donut"], ids=case_id)
def test_donut_alt_text_matches_the_shared_fixture(case):
    hl.use(brand=False, locale=case["locale"])
    assert figure_alt(hl.donut(frame_of(case), **case["options"])) == case["alt"]
    hl.use(brand=False)


@pytest.mark.parametrize("case", FIXTURE["likert"], ids=case_id)
def test_likert_alt_text_matches_the_shared_fixture(case):
    hl.use(brand=False, locale=case["locale"])
    assert figure_alt(hl.likert(frame_of(case), "item", "rating", **case["options"])) == case["alt"]
    hl.use(brand=False)

@pytest.mark.parametrize("case", FIXTURE["sankey"], ids=case_id)
def test_sankey_alt_text_matches_the_shared_fixture(case):
    hl.use(brand=False, locale=case["locale"])
    assert figure_alt(hl.sankey(frame_of(case), **case["options"])) == case["alt"]
    hl.use(brand=False)


@pytest.mark.parametrize("case", FIXTURE["chord"], ids=case_id)
def test_chord_alt_text_matches_the_shared_fixture(case):
    hl.use(brand=False, locale=case["locale"])
    assert figure_alt(hl.chord(frame_of(case), "source", "target", **case["options"])) == case["alt"]
    hl.use(brand=False)


@pytest.mark.parametrize("case", FIXTURE["venn"], ids=case_id)
def test_venn_alt_text_matches_the_shared_fixture(case):
    hl.use(brand=False, locale=case["locale"])
    assert figure_alt(hl.venn(frame_of(case), **case["options"])) == case["alt"]
    hl.use(brand=False)

@pytest.mark.parametrize("case", FIXTURE["correlation"], ids=case_id)
def test_correlation_alt_text_matches_the_shared_fixture(case):
    hl.use(brand=False, locale=case["locale"])
    assert figure_alt(hl.correlation(frame_of(case), **case["options"])) == case["alt"]
    hl.use(brand=False)


@pytest.mark.parametrize("case", FIXTURE["funnel"], ids=case_id)
def test_funnel_alt_text_matches_the_shared_fixture(case):
    hl.use(brand=False, locale=case["locale"])
    assert figure_alt(hl.funnel(frame_of(case), **case["options"])) == case["alt"]
    hl.use(brand=False)


@pytest.mark.parametrize("case", FIXTURE["prisma"], ids=lambda case: f"{case['locale']}-{sorted(case['counts'])}")
def test_prisma_alt_text_matches_the_shared_fixture(case):
    hl.use(brand=False, locale=case["locale"])
    assert figure_alt(hl.prisma(case["counts"])) == case["alt"]
    hl.use(brand=False)

@pytest.mark.parametrize("case", FIXTURE["risk_of_bias"], ids=case_id)
def test_risk_of_bias_alt_text_matches_the_shared_fixture(case):
    hl.use(brand=False, locale=case["locale"])
    assert figure_alt(hl.risk_of_bias(frame_of(case), "study", **case["options"])) == case["alt"]
    hl.use(brand=False)


@pytest.mark.parametrize("case", FIXTURE["arcs"], ids=case_id)
def test_arcs_alt_text_matches_the_shared_fixture(case):
    hl.use(brand=False, locale=case["locale"])
    assert figure_alt(hl.arcs(frame_of(case), "source", "target", **case["options"])) == case["alt"]
    hl.use(brand=False)


@pytest.mark.parametrize("case", FIXTURE["swimlanes"], ids=case_id)
def test_swimlanes_alt_text_matches_the_shared_fixture(case):
    hl.use(brand=False, locale=case["locale"])
    assert figure_alt(hl.swimlanes(frame_of(case), start="start", end="end", **case["options"])) == case["alt"]
    hl.use(brand=False)

def test_extremes_name_ties_together_and_leave_out_missing_values():
    entries = [("a", 2.0, "2"), ("b", float("nan"), ""), ("c", 5.0, "5"), ("d", 5.0, "5"), ("e", 1.0, "1")]
    assert extremes(entries, "en") == "Highest: c, d (5); lowest: e (1)."
    assert extremes([("a", 3.0, "3"), ("b", 3.0, "3")], "en") == "Every value 3."
    assert extremes([("a", float("nan"), "")], "en") == ""


def test_grid_extremes_name_the_first_point_reading_row_by_row():
    grid = np.array([[1.0, 9.0], [9.0, np.nan]])
    tips = {"x": ["8", "12"], "y": ["1", "2"], "z": [["1", "9"], ["9", ""]]}
    found = grid_extremes(grid, tips, {"x": "Hour", "y": "Week"}, "en")
    assert found == "Highest at Hour 12, Week 1 (9); lowest at Hour 8, Week 1 (1)."


def test_alt_text_reaches_the_files_and_can_be_replaced(tmp_path):
    hl.use(brand=False)
    figure = hl.bars(pd.DataFrame({"unit": ["ICU", "Ward"], "n": [12, 30]}), "unit", "n", title="Admissions")
    svg = hl.save(figure, tmp_path / "admissions", formats=["svg"])[0].read_text(encoding="utf-8")
    assert "<desc>Admissions. Bar chart. Highest: Ward (30); lowest: ICU (12).</desc>" in svg
    figure.description = "Bar chart. The ward admits more than twice as many."
    assert figure_alt(figure) == "Admissions. Bar chart. The ward admits more than twice as many."
    assert hl.figure("Plain").description is None


def test_heatmap_and_surface_describe_their_peak_in_the_locale():
    grid = pd.DataFrame([{"hour": hour, "week": week, "load": 0.1 * hour + week} for hour in (8, 12)
                         for week in (1, 2)])
    hl.use(brand=False, locale="de")
    heat = hl.heatmap(grid, "hour", "week", "load", x_title="Uhrzeit", y_title="Woche")
    assert heat.description == ("Heatmap. Am höchsten bei Uhrzeit 12, Woche 2 (3,2); am niedrigsten bei Uhrzeit 8, "
                                "Woche 1 (1,8).")
    hl.use(brand=False)
    assert hl.surface(grid, "hour", "week", "load").description.startswith("3D surface. Highest at Hour 12, Week 2")
