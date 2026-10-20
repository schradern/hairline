"""Inputs that once changed values, misrepresented data or lost files without an error."""

import base64
import re
import warnings
from importlib import resources
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import pytest
from PIL import Image

import hairline as hl
from hairline.charts.correlation import correlation_spec
from hairline.charts.donut import donut_rings
from hairline.charts.funnel import funnel_spec
from hairline.charts.prisma import prisma_spec
from hairline.charts.risk_of_bias import risk_of_bias_spec
from hairline.charts.timeseries import panel_stats
from hairline.charts.venn import venn_spec
from hairline.interactive import figure_targets
from hairline.numbers import format_number, format_p
from hairline.stats.distributions import chi2_sf, t_quantile
from hairline.stats.tests import kruskal, logrank, rank_sum


@pytest.mark.parametrize(("value", "digits", "expected"), [
    (500000000, 0, "500,000,000"), (1000000000, 0, "1,000,000,000"), (1000000000, 2, "1,000,000,000.00"),
    (1000000, 3, "1,000,000.000"), (1234.499999, 0, "1,234"), (8.645, 2, "8.65"), (2.5, 0, "3")])
def test_exact_values_stay_exact(value, digits, expected):
    assert format_number(value, digits, "en") == expected


def test_a_label_repeated_under_two_parents_counts_once():
    data = pd.DataFrame({"one": ["A", "B"], "two": ["Shared", "Shared"], "three": ["a", "b"], "n": [10, 30]})
    rings = donut_rings(data, None, "n", ["one", "two", "three"])
    assert [sum(item["value"] for item in ring) for ring in rings] == [40, 40, 40]
    assert [(item["name"], item["value"]) for item in rings[2]] == [("a", 10), ("b", 30)]


def three_arms() -> pd.DataFrame:
    times = list(range(1, 21)) + list(range(2, 22)) + [index / 100 for index in range(1, 21)]
    return pd.DataFrame({"time": times, "event": [1] * 60, "arm": ["A"] * 20 + ["B"] * 20 + ["C"] * 20})


def test_log_rank_covers_only_the_groups_drawn():
    figure = hl.kaplan_meier(three_arms(), "time", "event", by="arm", order=["A", "B"])
    assert ("Log-rank", "p = 0.50") in figure.headers[0].stats


def test_study_survival_tests_only_the_groups_it_reports():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        study = hl.study(three_arms(), group="arm", time="time", event="event", order=["A", "B"])
    result = study.survival()
    assert list(result.table["Group"]) == ["A", "B"]
    assert result.values["p"] == "p = 0.50"


def test_all_censored_groups_draw_without_a_test():
    data = pd.DataFrame({"time": [1, 2, 3, 4], "event": [0, 0, 0, 0], "arm": ["A", "A", "B", "B"]})
    assert np.isnan(logrank(data["time"], data["event"], data["arm"])["p"])
    figure = hl.kaplan_meier(data, "time", "event", by="arm")
    assert [label for label, _ in figure.headers[0].stats] == ["Median"]


def test_missing_follow_up_times_are_refused():
    with pytest.raises(ValueError, match="must not be missing; row 2"):
        hl.kaplan_meier(pd.DataFrame({"time": [1, np.nan, 3], "event": [1, 1, 0]}), "time", "event")


def failing_html(monkeypatch):
    import hairline.export as export
    original = export.write_one

    def failing(fig, path, name, dpi, options):
        if name == "html":
            raise ValueError("cannot read a missing value")
        original(fig, path, name, dpi, options)
    monkeypatch.setattr(export, "write_one", failing)


def test_a_failed_save_keeps_the_existing_files(tmp_path, monkeypatch):
    existing = tmp_path / "figure.png"
    existing.write_bytes(b"old figure")
    failing_html(monkeypatch)
    with pytest.raises(RuntimeError, match="missing value"):
        hl.save(hl.figure("T"), tmp_path / "figure", formats=["png", "html"], dpi=72)
    assert existing.read_bytes() == b"old figure"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["figure.png"]


def test_a_folder_in_the_way_stops_the_save_before_writing(tmp_path):
    existing = tmp_path / "figure.png"
    existing.write_bytes(b"old figure")
    (tmp_path / "figure.html").mkdir()
    with pytest.raises(RuntimeError, match="a folder of that name exists"):
        hl.save(hl.figure("T"), tmp_path / "figure", formats=["png", "html"], dpi=72)
    assert existing.read_bytes() == b"old figure"


def test_negative_segments_stack_below_zero():
    data = pd.DataFrame({"unit": ["Ward"] * 3, "part": ["a", "b", "c"], "change": [5, -3, 2]})
    figure = hl.bars(data, "unit", "change", by="part", stacked=True, horizontal=False)
    spans = [(patch.get_y(), patch.get_y() + patch.get_height()) for patch in figure.ax.patches]
    assert spans == [(0, 5), (0, -3), (5, 7)]
    totals = [text.get_text() for text in figure.ax.texts if text.get_gid() == "hairline-total"]
    assert totals == ["4"]


def test_percent_bars_refuse_a_category_without_a_total():
    data = pd.DataFrame({"unit": ["Ward", "Ward", "ICU"], "part": ["a", "b", "a"], "n": [1, 2, 0]})
    with pytest.raises(ValueError, match="'ICU' totals 0"):
        hl.bars(data, "unit", "n", by="part", stacked=True, percent=True)


def test_a_count_column_in_the_data_stays_a_category():
    data = pd.DataFrame({"Count": ["A", "A", "B"]})
    figure = hl.bars(data, "Count")
    assert figure.category_axes[(0, "x")] == ["A", "B"]
    assert figure.title == "Rows by Count"


def test_a_long_study_label_is_refused_rather_than_reversing_the_axis():
    data = pd.DataFrame({"study": ["Early mobilisation plus physiotherapy versus standard rehabilitation"],
                         "estimate": [1.0], "low": [0.5], "high": [2.0]})
    with pytest.raises(hl.HairlineLayoutError, match="leave 0 pt for the intervals"):
        hl.forest(data)
    hl.forest(data, size="double")


def test_threshold_shares_leave_missing_values_out():
    pairs = panel_stats(pd.Series([1.0, np.nan]), ["share_above"], False, 0.5, "Above")
    assert pairs == [("Above", "100%")]


def test_invalid_rolling_windows_are_refused():
    data = pd.DataFrame({"day": [1, 2, 3], "value": [2, 4, 8]})
    for window in (0, -1, 1.5):
        with pytest.raises(ValueError, match="window must be a whole number of 1 or more"):
            hl.timeseries(data, "day", "value", window=window)


def test_a_group_without_values_keeps_the_overview():
    data = pd.DataFrame({"arm": ["A"] * 3 + ["B"] * 3, "x": [1, 2, 3, np.nan, np.nan, np.nan]})
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = hl.study(data, group="arm", variables=["x"]).describe()
    assert result.figure is not None


def test_text_order_finds_numeric_groups():
    data = pd.DataFrame({"group": [1, 1, 2, 2], "value": [1.0, 2.0, 3.0, 4.0]})
    figure = hl.spread(data, "group", "value", order=["1", "2"])
    assert figure.title


def test_iterators_count_like_lists():
    spec = venn_spec({"A": iter([1, 2]), "B": iter([2, 3])})
    assert [entry["value"] for entry in spec["sets"]] == [2, 2]


@pytest.mark.parametrize("value", [-5, 3.4])
def test_prisma_counts_are_whole_and_not_negative(value):
    with pytest.raises(ValueError, match="counts must be whole numbers of 0 or more"):
        prisma_spec({"identified": 10, "screened": value, "included": 2})


def test_funnel_refuses_standard_errors_of_zero_or_less():
    data = pd.DataFrame({"ratio": [0.8, 1.1, 0.9], "se": [0.2, -0.1, 0.3]})
    with pytest.raises(ValueError, match="'se' is -0.1 in row 2"):
        funnel_spec(data, "ratio", "se")


def test_an_interval_needs_both_ends():
    data = pd.DataFrame({"unit": ["A"], "rate": [1.0], "low": [0.5]})
    with pytest.raises(ValueError, match="needs both low and high"):
        hl.dotplot(data, "unit", "rate", low="low")


def test_repeated_judgements_are_refused():
    data = pd.DataFrame({"study": ["S1", "S1", "S2"], "domain": ["D1", "D1", "D1"],
                         "judgement": ["low", "low", "high"]})
    with pytest.raises(ValueError, match="S1 has 2 judgements for D1"):
        risk_of_bias_spec(data, "study", "domain", "judgement")


def test_a_fit_without_spread_in_x_names_its_need():
    data = pd.DataFrame({"x": [1.0, 1.0, 1.0], "y": [1.0, 2.0, 3.0]})
    with pytest.raises(ValueError, match="2 different x values"):
        hl.scatter(data, "x", "y")


def test_a_constant_column_has_no_correlation():
    data = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [5.0, 5.0, 5.0]})
    with pytest.raises(ValueError, match="'b' has the same value in every complete row"):
        correlation_spec(data, None, "pearson")


def test_identical_samples_leave_the_test_undefined():
    assert np.isnan(rank_sum([1, 1, 1], [1, 1, 1]))
    assert np.isnan(kruskal([[2, 2], [2, 2], [2, 2]]))
    assert format_p(rank_sum([1, 1], [1, 1])) == "p not defined"


def test_raincloud_leaves_missing_values_out():
    data = pd.DataFrame({"group": ["A"] * 3, "value": [1.0, np.nan, 3.0]})
    figure = hl.raincloud(data, "group", "value")
    assert figure.ax.patches[-1].get_height() == pytest.approx(1.0)


def font_data(html: str) -> list[bytes]:
    return [base64.b64decode(data) for data in re.findall(r"base64,([A-Za-z0-9+/=]+)\) format", html)]


def test_html_embeds_the_requested_font_not_the_bundled_one(tmp_path):
    hl.use(font="DejaVu Sans")
    figure = hl.figure("Fonts")
    figure.ax.plot([0, 1], [0, 1])
    html = hl.save(figure, tmp_path / "fonts", formats=["html"])[0].read_text(encoding="utf-8")
    bundled = {(resources.files("hairline") / "data" / "fonts" / file).read_bytes()
               for file in hl.tokens.load_tokens()["interactive"]["fonts"]}
    embedded = font_data(html)
    assert "font-family:'DejaVu Sans'" in html and embedded
    assert not bundled & set(embedded)
    assert embedded[0] == Path(matplotlib.font_manager.findfont("DejaVu Sans")).read_bytes()


def test_tooltips_keep_the_locale_the_figure_was_made_in():
    hl.use(locale="de")
    figure = hl.figure("T")
    figure.ax.plot([1.1, 2.2], [1.1, 2.2], label="Series")
    hl.use(locale="en")
    texts = [tip["text"] for tip in figure_targets(figure)["series"][0]["tips"]]
    assert texts == ["Series: 1,1, 1,1", "Series: 2,2, 2,2"]


def test_tiff_names_its_figure(tmp_path):
    figure = hl.figure("Überleben", subtitle="Nach Gruppe")
    path = hl.save(figure, tmp_path / "named", formats=["tiff"], dpi=72)[0]
    with Image.open(path) as image:
        text = {tag: image.tag_v2[tag].encode("latin-1").decode("utf-8") for tag in (269, 270)}
        assert image.info["compression"] == "tiff_lzw"
    assert text == {269: "Überleben", 270: "Überleben. Nach Gruppe"}


def test_distributions_reach_far_tails():
    assert t_quantile(0.99999, 1) == pytest.approx(31830.988608, rel=1e-9)
    assert t_quantile(0.025, 3) == pytest.approx(-3.182446305284, rel=1e-9)
    assert chi2_sf(1e6, 1e6) == pytest.approx(0.499811936803, rel=1e-8)


def test_html_export_skips_missing_values(tmp_path):
    data = pd.DataFrame({"day": [1, 2, 3, 4], "value": [np.nan, 2.0, np.nan, 4.0]})
    figure = hl.timeseries(data, "day", "value", window=1)
    paths = hl.save(figure, tmp_path / "gaps", formats=["png", "html"], dpi=72)
    assert [path.name for path in paths] == ["gaps.png", "gaps.html"]
    tips = [tip["text"] for series in figure_targets(figure)["series"] for tip in series["tips"]]
    assert not any("nan" in text for text in tips)
