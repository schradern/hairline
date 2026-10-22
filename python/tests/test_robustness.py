"""Inputs that once changed values, misrepresented data or lost files without an error."""

import base64
import io
import json
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
from hairline.tokens import load_tokens


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
    with pytest.raises(hl.HairlineLayoutError, match="forest: the figure leaves .* pt for the table"):
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


def test_a_median_on_a_flat_half_is_the_middle_of_the_flat():
    from hairline.stats.survival import km_estimate, km_median
    assert km_median(km_estimate([1, 2, 3, 4], [1, 1, 1, 1])) == 2.5
    assert km_median(km_estimate([1, 2, 3, 4], [1, 1, 0, 0])) == 2.0


# Second stress test

def test_numbers_beyond_their_precision_do_not_round_up():
    assert format_number(999999999999999.4, 0, "en") == "999,999,999,999,999"
    assert format_number(1234567.345, 2, "en") == "1,234,567.35"
    assert format_number(np.nan, 1) == "–"
    assert format_number(np.inf, 0, "de") == "∞"


def test_small_or_tight_values_keep_their_digits():
    from hairline.numbers import auto_digits
    assert auto_digits([0.0004, 0.0003, 0.0005]) == 4
    assert auto_digits([1000.1, 1000.2, 1000.3]) == 1
    assert auto_digits([1, 2, 3]) == 0


def test_a_median_between_small_whole_numbers_keeps_its_half():
    from hairline.study.summaries import summary_numbers, summary_text

    def median_iqr(values):
        return summary_text(summary_numbers(np.array(values), ("median_iqr",), 0), "median_iqr", 0, whole=True)
    assert median_iqr([1.0, 2, 3, 4]) == "2.5 (1.8–3.3)"
    assert median_iqr([55.0, 56, 61, 70]) == "59 (56–63)"


def test_value_labels_keep_the_data_decimals():
    figure = hl.bars(pd.DataFrame({"g": list("ABC"), "v": [0.12, 0.08, 0.31]}), "g", "v")
    labels = sorted(text.get_text() for text in figure.ax.texts if text.get_gid() == "hairline-value")
    assert labels == ["0.08", "0.12", "0.31"]


def test_a_missing_group_label_is_named():
    data = pd.DataFrame({"arm": ["A", None, "B"], "sex": ["F", "F", "M"], "n": [30, 10, 60]})
    for draw in (lambda: hl.donut(data, levels=["arm", "sex"], value="n"), lambda: hl.bars(data, "arm", "n"),
                 lambda: hl.raincloud(data, "arm", "n")):
        with pytest.raises(ValueError, match="'arm' is missing in row 2"):
            draw()


def test_flows_skip_missing_values_and_refuse_self_flows():
    from hairline.charts.chord import chord_spec
    data = pd.DataFrame({"s": ["A", "A", "B"], "t": ["x", "x", "x"], "v": [5.0, np.nan, 3]})
    assert sorted(link["value"] for link in chord_spec(data, "s", "t", "v")["links"]) == [3, 5]
    with pytest.raises(ValueError, match="A → A flows to itself"):
        chord_spec(pd.DataFrame({"s": ["A", "A"], "t": ["A", "B"], "v": [10, 1]}), "s", "t", "v")


def test_arcs_combine_both_directions():
    from hairline.charts.arcs import arcs_spec
    spec = arcs_spec(pd.DataFrame({"s": ["A", "B"], "t": ["B", "A"], "v": [2, 3]}), "s", "t", "v")
    assert [(link["pair"], link["value"]) for link in spec["links"]] == [("A ↔ B", 5.0)]
    assert [entry["value"] for entry in spec["key"]] == [2.0, 5.0]


def test_an_order_naming_no_group_is_refused():
    with pytest.raises(ValueError, match="order names 'C', which is not a group"):
        hl.spread(pd.DataFrame({"g": ["A", "B"], "v": [1.0, 2.0]}), "g", "v", order=["A", "C"])


def test_categories_keep_their_order():
    data = pd.DataFrame({"level": pd.Categorical(["high", "low", "mid"], ["low", "mid", "high"], ordered=True),
                         "n": [1, 2, 3]})
    assert hl.bars(data, "level", "n", sort="given").category_axes[(0, "x")] == ["low", "mid", "high"]


def test_empty_input_draws_nothing_silently():
    empty = pd.DataFrame({"g": pd.Series([], dtype=str), "h": pd.Series([], dtype=str),
                          "v": pd.Series([], dtype=float)})
    with pytest.raises(ValueError, match="no flows above zero"):
        hl.sankey(empty, ["g", "h"], "v")
    with pytest.raises(ValueError, match="no colour sets named"):
        hl.swatches([])


def test_upright_labels_keep_their_room_when_the_figure_fits_its_height():
    data = pd.DataFrame({"g": ["Intensive care unit of the university hospital", "Ward B"], "h": ["z", "w"],
                         "v": [1, 2]})
    figure = hl.arcs(data, "g", "h", "v")
    figure.figure.canvas.draw()
    assert figure.figure.get_size_inches()[1] * 72 > 145
    assert min(point[1] for shape in figure.shapes if shape["kind"] == "line" for point in shape["points"]) > 0


def test_log_rank_follows_survdiff_where_groups_have_no_expected_events():
    assert np.isnan(logrank([1, 2, 3, 4, 5, 6], [0, 0, 0, 0, 1, 0], list("AABBCC"))["p"])
    assert np.isnan(logrank([3] * 6, [1] * 6, list("AABBCC"))["p"])
    assert logrank(list(range(1, 7)), [1] * 6, list("abcdef"))["p"] == pytest.approx(0.09259092767611, rel=1e-9)


def test_forest_refuses_values_it_cannot_draw():
    rows = pd.DataFrame({"study": ["S"], "estimate": [5.0], "low": [0.9], "high": [1.6]})
    with pytest.raises(ValueError, match="outside its interval"):
        hl.forest(rows)
    with pytest.raises(ValueError, match="must be numbers"):
        hl.forest(rows.assign(estimate=np.nan))
    with pytest.raises(ValueError, match="favours takes two labels"):
        hl.forest(rows.assign(estimate=1.0), favours=["A"])


def test_forest_digits_follow_small_values():
    from hairline.charts.forest import forest_spec
    rows = pd.DataFrame({"study": ["S"], "estimate": [0.0004], "low": [0.0003], "high": [0.0005]})
    spec = forest_spec(rows, "study", "estimate", "low", "high", ratio=False, color="#000000")
    assert spec["rows"][0]["effect_text"] == "0.0004 [0.0003; 0.0005]"
    assert len(set(spec["axis"]["labels"])) == len(spec["axis"]["labels"])


def test_egger_needs_three_studies_with_different_errors():
    from hairline.stats.tests import egger
    assert np.isnan(egger([0.1, 0.2], [0.1, 0.2]))
    assert np.isnan(egger([0.1, 0.2, 0.3], [0.1, 0.1, 0.1]))


def test_date_tooltips_keep_the_time_zone_and_the_clock():
    x = pd.date_range("2024-03-01", periods=2, tz="Europe/Berlin", freq="h")
    figure = hl.timeseries(pd.DataFrame({"x": x, "y": [1.5, 2.5]}), "x", "y", window=1)
    texts = [tip["text"] for series in figure_targets(figure)["series"] for tip in series["tips"]]
    assert texts[:2] == ["Y over time: 2024-03-01 00:00, 1.5", "Y over time: 2024-03-01 01:00, 2.5"]


def test_scatter_fits_the_points_it_draws():
    data = pd.DataFrame({"x": range(30), "y": [float(index % 7) for index in range(30)], "g": list("ABC") * 10})
    figure = hl.scatter(data, "x", "y", by="g", order=["A", "B"])
    assert ("n", "20") in figure.headers[0].stats


def test_numpy_numbers_count_as_numbers():
    prisma_spec({"identified": np.int64(100), "screened": np.int64(100), "included": np.int64(10)})
    hl.timeseries(pd.DataFrame({"x": [1, 2, 3], "y": [1.0, 2, 3]}), "x", "y", window=np.int64(2))


def test_venn_leaves_missing_values_out():
    spec = venn_spec({"A": pd.Series([1, 2, np.nan]), "B": pd.Series([2, np.nan, np.nan])})
    assert [entry["value"] for entry in spec["sets"]] == [2, 1]


def test_ridgeline_shows_constant_groups():
    data = pd.DataFrame({"g": ["A"] * 10 + ["B"] * 10, "v": [5.0] * 10 + list(np.linspace(0, 1, 10))})
    figure = hl.ridgeline(data, "g", "v")
    assert any(list(line.get_xdata()) == [5.0, 5.0] for line in figure.ax.lines)


def test_study_names_the_column_it_cannot_use():
    data = pd.DataFrame({"g": ["a", "b"] * 3, "x": [1.0, 2, 3, 4, 5, 6],
                         "day": pd.date_range("2025-01-01", periods=6)})
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        study = hl.study(data, group="g")
    assert study.variables == ["x"]
    with pytest.raises(ValueError, match="'nope' is not a column of the study"):
        study.compare("nope")
    with pytest.raises(ValueError, match="no rows"):
        hl.study(data.iloc[:0], group="g")
    assert study.describe(stats="median_iqr").table is not None


def test_save_reads_options_as_given(tmp_path):
    figure = hl.figure("T")
    paths = hl.save(figure, tmp_path / "f", formats=["PNG", "png"], dpi=72, background="#ffeedd")
    assert [path.name for path in paths] == ["f.png"]
    with Image.open(paths[0]) as image:
        assert image.convert("RGB").getpixel((1, 1)) == (255, 238, 221)
    with pytest.raises(ValueError, match="dpi must be a number above zero"):
        hl.save(figure, tmp_path / "g", formats=["png"], dpi=0)
    long_name = tmp_path / ("x" * 240)
    assert hl.save(figure, long_name, formats=["png"], dpi=72)[0].exists()


def test_use_refuses_sizes_of_zero_or_less():
    with pytest.raises(ValueError, match="base_size must be a number above zero"):
        hl.use(base_size=0)
    with pytest.raises(ValueError, match="palette has no colours"):
        hl.use(palette=[])


def test_greek_letters_fall_back_to_a_font_that_has_them():
    from hairline.layout.measure import font
    assert font("Hairline Sans", 9).get_family() == ["Hairline Sans", "DejaVu Sans"]


def test_kaplan_meier_handles_large_cohorts_quickly():
    import time as clock
    generator = np.random.default_rng(1)
    started = clock.perf_counter()
    from hairline.stats.survival import km_estimate
    km_estimate(generator.exponential(10, 50000).round(2), generator.integers(0, 2, 50000))
    assert clock.perf_counter() - started < 2


# Third review

def test_models_fitted_from_arrays_keep_their_terms():
    from types import SimpleNamespace

    from hairline.charts.forest import model_table
    model = SimpleNamespace(params=np.array([0.1, 1.2, -0.3]),
                            conf_int=lambda: np.array([[0.0, 0.2], [1.0, 1.4], [-0.5, -0.1]]),
                            model=SimpleNamespace(exog_names=["const", "x1", "x2"]))
    table = model_table(model, False)
    assert list(table["term"]) == ["x1", "x2"] and list(table["low"]) == [1.0, -0.5]


def test_a_group_named_twice_in_order_is_refused():
    data = pd.DataFrame({"g": ["A"] * 3 + ["B"] * 4, "v": [1.0, 2, 3, 4, 5, 6, 7]})
    with pytest.raises(ValueError, match="order names 'A' more than once"):
        hl.raincloud(data, "g", "v", order=["A", "A", "B"])


def test_labels_that_read_the_same_are_refused():
    data = pd.DataFrame({"parent": [1, "1"], "child": ["x", "y"], "value": [10, 30]})
    with pytest.raises(ValueError, match="holds 1 and '1', which read the same"):
        hl.partition(data, ["parent", "child"], "value")


def test_negative_bars_have_proper_targets():
    figure = hl.bars(pd.DataFrame({"g": ["A", "B"], "v": [-3.0, 2.0]}), "g", "v", sort="given", horizontal=False)
    series = figure_targets(figure)["series"][0]
    assert all(mark["rect"][2] > 0 and mark["rect"][3] > 0 for mark in series["marks"])
    assert [tip["text"].split(", ")[-1] for tip in series["tips"]] == ["−3", "2"]


def test_delayed_entry_counts_only_those_who_have_entered():
    from lifelines import KaplanMeierFitter

    from hairline.charts.kaplan_meier import at_risk_from, fitter_table
    table, total = fitter_table(KaplanMeierFitter().fit([2, 4, 6, 8], [1, 0, 1, 0], entry=[0, 0, 3, 5]))
    assert at_risk_from(table, total, [0, 2.5, 4.5, 6.5]) == [2, 1, 1, 1]


def test_tooltips_show_seconds_when_the_data_has_them():
    x = pd.to_datetime(["2025-01-01 10:00:01", "2025-01-01 10:00:02", "2025-01-01 10:00:03"])
    figure = hl.timeseries(pd.DataFrame({"x": x, "y": [1.0, 2, 3]}), "x", "y", window=1)
    texts = [tip["text"] for series in figure_targets(figure)["series"] for tip in series["tips"]]
    assert [text.split(": ", 1)[1].split(",")[0] for text in texts[:3]] == [
        "2025-01-01 10:00:01", "2025-01-01 10:00:02", "2025-01-01 10:00:03"]


def test_iso_text_across_a_clock_change_reads_in_utc():
    data = pd.DataFrame({"x": ["2025-03-30T00:00+01:00", "2025-03-30T04:00+02:00"], "y": [1.0, 2.0]})
    figure = hl.timeseries(data, "x", "y", window=1)
    assert figure.title


def quiet_study(data: pd.DataFrame, **roles) -> hl.Study:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return hl.study(data, **roles)


def visits() -> pd.DataFrame:
    """Three patients measured on several days: rows are visits, not patients."""
    return pd.DataFrame({"patient": [1, 1, 1, 2, 2, 3], "arm": ["A", "A", "A", "B", "B", "B"],
                         "day": ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-01", "2025-01-02", "2025-01-01"],
                         "lactate": [2.1, 2.4, 2.0, 3.1, 2.9, 2.5]})


def test_repeated_rows_of_one_id_are_not_counted_as_patients():
    study = quiet_study(visits(), group="arm", id="patient", variables=["lactate"], units={"lactate": "mmol/l"})
    for endpoint in (study.describe, lambda: study.compare("lactate"), lambda: study.distribution("lactate")):
        with pytest.raises(ValueError, match=r"id 1 has 3 rows in 'patient'.*one row per id first"):
            endpoint()
    assert study.over_time("day", "lactate").numbers["rows"]["analysed"] == 6


def test_an_id_repeated_where_the_value_is_missing_is_still_refused():
    # Counts take every row: four patients in five rows would read "5 patients: 3 in A and 2 in B".
    data = pd.DataFrame({"id": [1, 1, 2, 3, 4], "arm": ["A", "A", "A", "B", "B"], "age": [60.0, None, 72, 65, 58]})
    study = quiet_study(data, group="arm", id="id", variables=["age"], unit="patients")
    for endpoint in (study.describe, lambda: study.compare("age")):
        with pytest.raises(ValueError, match="id 1 has 2 rows in 'id'"):
            endpoint()


def test_results_say_how_many_rows_were_left_out():
    data = pd.DataFrame({"arm": ["A"] * 50 + ["B"] * 50, "score": [float(value) for value in range(82)] + [None] * 18})
    result = quiet_study(data, group="arm", variables=["score"], unit="patients").compare("score")
    assert result.text.endswith(" 82 of 100 patients; 18 without a value were left out.")
    assert result.numbers["rows"] == {"total": 100, "analysed": 82, "missing": {"variable": 18, "group": 0},
                                      "other_groups": 0}
    assert [result.numbers["groups"][name]["n"] for name in "AB"] == [50, 32]
    assert result.numbers["groups"]["B"]["missing"] == 18
    assert result.table["n"].tolist()[:2] == ["50", "32"]


def test_survival_counts_rows_without_a_group():
    data = three_arms().assign(arm=["A"] * 20 + ["B"] * 19 + [None] + ["C"] * 20)
    result = quiet_study(data, group="arm", time="time", event="event").survival()
    assert result.numbers["rows"] == {"total": 60, "analysed": 59, "missing": {"group": 1}, "other_groups": 0}
    assert result.text.endswith(" 59 of 60 participants; 1 without a group was left out.")
    assert result.numbers["test"]["method"] == "Log-rank" and result.numbers["test"]["df"] == 2


def test_numbers_keep_what_the_text_rounds():
    data = pd.DataFrame({"arm": ["A"] * 3 + ["B"] * 3, "score": [11.0, 12.0, 12.0, 12.0, 12.0, 12.0]})
    result = quiet_study(data, group="arm", variables=["score"], types={"score": "numeric"}).compare("score")
    assert result.numbers["groups"]["A"]["q1"] == 11.5 and result.values["groups"]["A"] == "12 (12–12)"
    test = result.numbers["test"]
    assert (test["method"], test["statistic"]) == ("Wilcoxon rank-sum", 3.0) and 0 < test["p"] < 1
    tied = quiet_study(data.assign(score=2.0), group="arm", variables=["score"], types={"score": "numeric"})
    test = tied.compare("score").numbers["test"]
    assert np.isnan(test["p"]) and "df" not in test


class Factor:
    """A formula factor as patsy names it."""
    def name(self):
        return "sex"


def test_effects_name_the_reference_level_of_a_formula_model():
    from types import SimpleNamespace
    factor = Factor()
    info = SimpleNamespace(
        term_codings={"sex": [SimpleNamespace(contrast_matrices={factor: SimpleNamespace(matrix=[[0.0], [1.0]])})]},
        factor_infos={factor: SimpleNamespace(categories=("Female", "Male"))})

    class Model:
        params = pd.Series({"Intercept": -1.2, "sex[T.Male]": 0.4})
        model = SimpleNamespace(data=SimpleNamespace(design_info=info))

        def conf_int(self):
            return pd.DataFrame({0: self.params - 0.3, 1: self.params + 0.3})
    study = quiet_study(pd.DataFrame({"sex": ["Female", "Male"]}))
    result = study.effects(Model(), exponentiate=True)
    assert result.numbers["reference"] == {"sex": "Female"} and result.numbers["scale"] == "ratio"
    assert result.numbers["terms"]["sex[T.Male]"]["estimate"] == pytest.approx(np.exp(0.4))
    table = pd.DataFrame({"study": ["age"], "estimate": [0.5], "low": [0.1], "high": [0.9]})
    assert study.effects(table).numbers == {"scale": "difference", "reference": {},
                                            "terms": {"age": {"estimate": 0.5, "low": 0.1, "high": 0.9}}}


def two_arms() -> pd.DataFrame:
    return pd.DataFrame({"arm": ["A"] * 3 + ["B"] * 4, "value": [1.0, 2, 3, 4, 5, 6, 7]})


def test_order_names_each_group_once():
    with pytest.raises(ValueError, match="hairline: study: order names 'A' twice"):
        quiet_study(two_arms(), group="arm", order=["A", "A", "B"])


def test_a_variable_may_share_the_internal_group_name():
    study = quiet_study(two_arms().rename(columns={"value": "_group"}), group="arm", variables=["_group"])
    result = study.compare("_group")
    assert result.numbers["test"]["method"] == "Wilcoxon rank-sum" and result.values["p"] == "p = 0.052"
    assert study.distribution("_group").numbers["groups"]["B"]["median"] == 5.5


def test_a_group_called_overall_keeps_its_own_column():
    data = two_arms().assign(arm=["Overall"] * 3 + ["B"] * 4)
    result = quiet_study(data, group="arm", variables=["value"]).describe()
    assert list(result.table.columns) == ["Characteristic", "Overall", "B", "Overall (all)"]
    assert result.values["n"] == {"Overall": "3", "B": "4", "Overall (all)": "7"}
    assert result.numbers["variables"]["value"]["Overall"]["median"] == 2.0


def test_a_group_without_rows_is_an_error_not_a_crash():
    empty = quiet_study(two_arms().assign(arm=None), group="arm", variables=["value"])
    for endpoint in (empty.describe, lambda: empty.compare("value"), lambda: empty.distribution("value")):
        with pytest.raises(ValueError, match="arm: no row has a group"):
            endpoint()
    elsewhere = quiet_study(two_arms(), group="arm", variables=["value"], order=["C"])
    with pytest.raises(ValueError, match="order names none of the groups in the data.*data: A, B"):
        elsewhere.describe()


def test_empty_stats_are_refused():
    study = quiet_study(two_arms(), group="arm", variables=["value"])
    with pytest.raises(ValueError, match="stats is empty"):
        study.distribution("value", stats=[])


def test_rows_in_groups_left_out_of_order_are_counted():
    data = two_arms().assign(arm=list("AABBBCC"))
    study = quiet_study(data, group="arm", variables=["value"], order=["A", "B"])
    result = study.compare("value")
    assert result.numbers["rows"] == {"total": 7, "analysed": 5, "missing": {"variable": 0, "group": 0},
                                      "other_groups": 2}
    assert result.text.endswith(" 5 of 7 participants; 2 in groups not named in order were left out.")
    assert study.describe().numbers["rows"]["missing"] == {"group": 0}
    assert study.describe().text.endswith(" 2 in groups not named in order are counted in Overall only.")


# Fourth review

def test_a_group_left_out_of_order_leaves_no_rows_in_the_test():
    counts = {"A": {"Low": 8, "High": 2}, "B": {"Low": 2, "High": 8}, "C": {"OnlyC": 1, "OtherC": 1}}
    rows = [(group, outcome) for group, kinds in counts.items() for outcome, count in kinds.items()
            for _ in range(count)]
    data = pd.DataFrame(rows, columns=["arm", "outcome"])
    result = quiet_study(data, group="arm", variables=["outcome"], order=["A", "B"]).compare("outcome")
    assert (result.numbers["test"]["df"], round(result.numbers["test"]["p"], 8)) == (1, 0.00729036)
    assert list(result.table.iloc[:-1, 0]) == ["High", "Low"]


def test_sparse_two_by_two_tables_use_fishers_exact_test():
    data = pd.DataFrame({"arm": ["A", "A", "B", "B"], "response": ["yes", "yes", "no", "no"]})
    result = quiet_study(data, group="arm", variables=["response"]).compare("response")
    assert result.numbers["test"]["method"] == "Fisher's exact test"
    assert result.numbers["test"]["p"] == pytest.approx(1 / 3)


def test_survival_refuses_repeated_ids():
    data = pd.DataFrame({"id": [1, 2, 3, 3, 4, 5], "arm": ["A", "A", "A", "A", "B", "B"],
                         "t": [1.0, 2, 3, 3, 4, 5], "e": [0, 0, 1, 1, 1, 1]})
    with pytest.raises(ValueError, match="id 3 has 2 rows in 'id'"):
        quiet_study(data, group="arm", id="id", time="t", event="e").survival()


def test_rank_sum_keeps_far_tails_in_either_order():
    first, second = list(range(50)), list(range(50, 100))
    assert rank_sum(first, second) == rank_sum(second, first) == pytest.approx(7.066071930389029e-18, rel=1e-9)


def test_one_value_has_no_standard_deviation():
    data = pd.DataFrame({"x": [60.0]})
    result = quiet_study(data, variables=["x"], types={"x": "numeric"}).distribution("x", stats=["mean_sd"])
    assert result.values["groups"]["Overall"] == "60.0 (–)"
    assert np.isnan(result.numbers["groups"]["Overall"]["sd"])


def test_a_group_named_test_keeps_its_summary():
    data = pd.DataFrame({"arm": ["control"] * 3 + ["test"] * 3, "score": [1.0, 2, 3, 4, 5, 6]})
    result = quiet_study(data, group="arm", variables=["score"]).compare("score")
    assert result.values["groups"]["test"] == "5 (4.5–5.5)" and result.values["test"] == "Wilcoxon rank-sum"


def test_over_time_reads_a_clock_change():
    data = pd.DataFrame({"t": ["2025-03-30T01:30:00+01:00", "2025-03-30T03:30:00+02:00", "2025-03-30T04:30:00+02:00"],
                         "v": [1.0, 2.0, 3.0]})
    result = quiet_study(data, variables=["v"], types={"v": "numeric"}).over_time("t", "v", window=1)
    assert result.numbers["rows"]["analysed"] == 3


def host_width(tmp_path, monkeypatch, **values) -> None:
    """Point hairline at a host context with these values, re-read on the next figure."""
    import json

    from hairline import host
    path = tmp_path / f"context-{len(list(tmp_path.glob('context-*')))}.json"
    path.write_text(json.dumps({"version": 1, "host": "x", "output": "pdf", **values}))
    monkeypatch.setenv(host.ENVIRONMENT, str(path))
    host._state.update(path=None, context=None)


def test_fitting_the_height_never_rasterises_the_figure(tmp_path, monkeypatch):
    """A 4 m figure once took 2.8 GB to fit its height (and 100 m filled the machine): the fit drew the whole
    provisional figure as pixels. It only needs the frame laid out."""
    from matplotlib.backends import backend_agg
    host_width(tmp_path, monkeypatch, width_mm=100000)
    hl.use(brand=False)

    def refuse(*_args, **_kwargs):
        raise AssertionError("the height fit allocated a raster")
    monkeypatch.setattr(backend_agg, "RendererAgg", refuse)
    data = pd.DataFrame({"g": ["a"] * 8 + ["b"] * 8, "v": np.arange(16.0)})
    figure = hl.spread(data, "g", "v")
    assert figure.figure.get_size_inches()[0] * 25.4 == pytest.approx(100000)


def test_a_raster_beyond_the_pixel_budget_is_refused_before_it_is_allocated(tmp_path):
    hl.use(brand=False)
    figure = hl.figure("Too large", width_mm=1200, height_mm=900)
    with pytest.raises(ValueError, match="megapixels, more than the 600 a raster image may have"):
        figure.figure.savefig(tmp_path / "x.png", dpi=600)
    with pytest.raises(ValueError, match="1200 x 900 mm figure at 600 dpi"):
        hl.save(figure, tmp_path / "x", formats=["pdf", "tiff"])
    assert not list(tmp_path.iterdir())
    assert [path.name for path in hl.save(figure, tmp_path / "x", formats=["pdf", "svg"])] == ["x.pdf", "x.svg"]


def test_host_sizes_that_are_no_numbers_above_zero_are_left_out(tmp_path, monkeypatch):
    for value in ("85", -50, 0, True, [85], float("inf")):
        host_width(tmp_path, monkeypatch, width_mm=value, dpi="high")
        with pytest.warns(UserWarning, match="must be a number above zero; continuing without it"):
            hl.use(brand=False)
            figure = hl.figure("Default width")
        assert figure.figure.get_size_inches()[0] * 25.4 == pytest.approx(120)


def test_an_explicit_size_must_be_a_number_above_zero():
    hl.use(brand=False)
    for width in (0, -10, float("nan")):
        with pytest.raises(ValueError, match="width_mm must be a number above zero"):
            hl.figure("No size", width_mm=width)


def test_a_rejected_use_does_not_come_back_with_the_next_host_context(tmp_path, monkeypatch):
    hl.use(brand=False)
    with pytest.raises(ValueError, match="base_size must be a number above zero"):
        hl.use(brand=False, base_size=-1)
    host_width(tmp_path, monkeypatch, width_mm=85)
    assert hl.figure("After a failed use()").figure.get_size_inches()[0] * 25.4 == pytest.approx(85)


INF = float("inf")
FRAME = pd.DataFrame({"g": ["a", "b", "c"], "v": [1.0, 2.0, 3.0]})


@pytest.mark.parametrize(("draw", "message"), [
    (lambda: hl.donut(FRAME.assign(v=[1, INF, 3]), "g", "v"), "'v' is infinite in row 2"),
    (lambda: hl.sankey(pd.DataFrame({"a": ["x"], "b": ["y"], "n": [INF]}), ["a", "b"], "n"), "'n' is infinite"),
    (lambda: hl.chord(pd.DataFrame({"a": ["x"], "b": ["y"], "n": [INF]}), "a", "b", "n"), "'n' is infinite"),
    (lambda: hl.scatter(pd.DataFrame({"x": [1.0, INF, 3], "y": [1.0, 2, 3]}), "x", "y"), "'x' is infinite"),
    (lambda: hl.spread(FRAME.assign(v=[1, 2, -INF]), "g", "v"), "'v' is infinite in row 3"),
    (lambda: hl.kaplan_meier(pd.DataFrame({"t": [1.0, INF], "e": [1, 0]}), "t", "e"), "'t' is infinite"),
    (lambda: hl.prisma({"identified": INF, "screened": 10, "included": 2}), "identified is inf"),
    (lambda: hl.spread(FRAME, "g", "v", marks={"a": INF}), "the mark for 'a' is inf"),
    (lambda: hl.spread(FRAME, "g", "v", marks={"typo": 5}), "marks names 'typo', which is not a group drawn"),
    (lambda: hl.spread(FRAME, "g", "v", stats=["median", "median"]), "stats names 'median' twice"),
    (lambda: hl.spread(FRAME, "g", "v", digits=1.5), "digits must be a whole number"),
    (lambda: hl.bars(FRAME.assign(v=["1", "2", "3"]), "g", "v"), "'v' holds .* values; it needs numbers"),
    (lambda: hl.bars(pd.DataFrame({"g": ["a", "a"], "s": ["x", "y"], "v": [-1.0, 2.0]}), "g", "v", by="s",
                     stacked=True, percent=True), "percent needs values of zero or more"),
    (lambda: hl.funnel(pd.DataFrame({"e": [1.0, 1.2, 1.3], "s": [20.0, 0.2, 0.3]}), "e", "s"),
     "standard error of 20 puts the funnel's limits beyond ratios"),
    (lambda: hl.raincloud(FRAME.assign(v=[np.nan] * 3), "g", "v"), "no values to draw"),
    (lambda: hl.kaplan_meier(pd.DataFrame({"t": [1.0, 2.0], "e": [1, 0]})), "name the time and event columns"),
    (lambda: hl.kaplan_meier(pd.DataFrame({"t": [1.0, 2.0], "e": [1, 0]}), "t", "e", stats=["x"]),
     "stats are \\(label, value\\) pairs"),
    (lambda: hl.prisma({"identified": 10, "screened": 8, "included": 2, "excluded_reasons": [1, 2]}),
     "excluded_reasons is \\[1, 2\\]"),
    (lambda: hl.timeseries(pd.DataFrame({"t": pd.date_range("2024-01-01", periods=5), "v": range(5)}), "t", "v",
                           events=[{"x": 5}]), "event x 5 is not a date"),
    (lambda: hl.swatches([]), "no colour sets named"),
])
def test_input_that_cannot_be_drawn_gets_a_hairline_message(draw, message):
    hl.use(brand=False)
    with pytest.raises(ValueError, match=message):
        figure = draw()
        figure.figure.savefig(io.BytesIO(), format="png", dpi=30)


def test_an_empty_order_is_no_order():
    hl.use(brand=False)
    assert [text.get_text() for text in hl.bars(FRAME, "g", "v", order=[]).ax.get_xticklabels()]


def test_labels_that_leave_no_room_for_the_panel_are_refused():
    hl.use(brand=False)
    data = pd.DataFrame({"g": ["Intensive care unit of the university hospital, north wing, level three", "B"],
                         "v": [12.0, 7.0]})
    with pytest.raises(hl.HairlineLayoutError, match="figure too narrow: .* the y labels take"):
        figure = hl.bars(data, "g", "v", size="single")
        figure.figure.savefig(io.BytesIO(), format="png", dpi=30)


def test_many_dotplot_rows_grow_the_figure_instead_of_overlapping():
    hl.use(brand=False)
    rows = pd.DataFrame({"name": [f"Row {index}" for index in range(30)], "e": np.linspace(1, 2, 30)})
    rows = rows.assign(low=rows.e - 0.2, high=rows.e + 0.2)
    figure = hl.dotplot(rows, "name", "e", "low", "high")
    names = sorted(shape["y"] for shape in figure.shapes if shape["kind"] == "text" and shape["text"].startswith("Row"))
    assert min(b - a for a, b in zip(names, names[1:], strict=False)) > figure.settings.base_size


def test_host_locales_follow_language_tags_and_unknown_ones_are_left_out(tmp_path, monkeypatch):
    host_width(tmp_path, monkeypatch, locale="de-DE")
    hl.use(brand=False)
    assert hl.figure("Deutsch").settings.locale == "de"
    host_width(tmp_path, monkeypatch, locale="fr")
    with pytest.warns(UserWarning, match="locale 'fr' is not one of de, en"):
        hl.figure("Français")


def test_the_first_figure_after_a_new_host_context_has_its_style(tmp_path, monkeypatch):
    hl.use(brand=False)
    hl.figure("Before")
    host_width(tmp_path, monkeypatch, locale="de", base_size=11)
    figure = hl.figure("After")
    assert (figure.settings.locale, figure.settings.base_size) == ("de", 11)


def test_a_damaged_manifest_is_replaced_instead_of_stopping_every_figure(tmp_path, monkeypatch):
    folder = tmp_path / "figures"
    folder.mkdir()
    (folder / "hairline-figures.json").write_text("{broken")
    host_width(tmp_path, monkeypatch, figure_dir=str(folder), interactive="false", output="html")
    hl.use(brand=False)
    figure = hl.figure("Handed off")
    figure.ax.plot([0, 1], [0, 1])
    with pytest.warns(UserWarning, match="is not a list of figures; starting a new one"):
        figure.figure.savefig(io.BytesIO(), format="png")
    entries = json.loads((folder / "hairline-figures.json").read_text())
    assert len(entries) == 1 and "html" not in entries[0]["files"]


def test_a_background_that_is_no_colour_is_refused_and_leaves_the_session_as_it_was():
    hl.use(brand=False)
    with pytest.raises(ValueError, match="background 'notacolor' is not a colour"):
        hl.use(brand=False, background="notacolor")
    hl.figure("Still drawn").figure.savefig(io.BytesIO(), format="png", dpi=30)


def test_an_empty_save_name_is_refused(tmp_path):
    hl.use(brand=False)
    with pytest.raises(ValueError, match="name must be a file path"):
        hl.save(hl.figure("No name"), "")


def study_frame() -> pd.DataFrame:
    return pd.DataFrame({"g": ["A"] * 4 + ["B"] * 4, "x": [1.0, 2, 3, 4, 5, 6, 7, 8], "id": list("abcdefgh"),
                         "t": [1.0, 2, 3, 4, 5, 6, 7, 8], "e": [1, 0, 1, 0, 1, 0, 1, 0]})


def test_study_refuses_order_without_a_group_and_names_numeric_groups_as_text():
    with pytest.raises(ValueError, match="order lists groups, but no group column is given"):
        quiet_study(study_frame(), time="t", event="e", order=["A", "B"])
    numeric = study_frame().assign(g=[2] * 4 + [1] * 4)
    assert quiet_study(numeric, group="g", variables=["x"], order=[2, 1]).groups == ["2", "1"]


def test_study_values_that_are_no_finite_numbers_are_errors_the_endpoints_name():
    data = study_frame().assign(x=[1.0, 2, INF, 4, 5, 6, 7, 8], y=["1", "<5", "3", "4", "5", "6", "7", "8"])
    study = quiet_study(data, group="g", variables=["x", "y"], types={"y": "numeric"})
    with pytest.raises(ValueError, match="1 value is infinite \\('inf'\\)"):
        study.compare("x")
    with pytest.raises(ValueError, match="1 value is not a number \\('<5'\\)"):
        study.distribution("y")


def test_a_repeated_index_with_ids_is_no_problem():
    data = study_frame()
    data.index = [0] * len(data)
    data.loc[:, "id"] = list("abcdefga")
    assert quiet_study(data, group="g", id="id", variables=["x"]).checks


def test_distribution_draws_the_groups_that_have_values():
    data = study_frame().assign(x=[np.nan] * 4 + [5.0, 6, 7, 8])
    result = quiet_study(data, group="g", variables=["x"]).distribution("x")
    assert result.figure is not None and result.table["n"].tolist()[:2] == ["0", "4"]


def test_effects_refuse_a_term_named_twice_and_sentences_keep_acronyms():
    table = pd.DataFrame({"study": ["Age", "Age"], "estimate": [1.1, 1.2], "low": [1.0, 1.1], "high": [1.2, 1.3]})
    with pytest.raises(ValueError, match="the term 'Age' is named in more than one row"):
        quiet_study(study_frame(), group="g", variables=["x"]).effects(table)
    study = quiet_study(study_frame(), group="g", time="t", event="e", labels={"t": "PFS", "g": "Treatment arm"})
    assert study.survival().text.startswith("Median PFS")
    assert "by treatment arm" in study.compare("x").figure.title


def test_numeric_levels_read_the_same_in_both_languages():
    from hairline.study.columns import level_text
    assert [level_text(value) for value in (0.1 + 0.2, 0.3, 1e-4, -0.0, 3.0, 2.5)] == \
        ["0.3", "0.3", "0.0001", "0", "3", "2.5"]


def test_study_refuses_a_variable_named_twice():
    with pytest.raises(ValueError, match="variables names 'x' twice"):
        quiet_study(study_frame(), group="g", variables=["x", "x"])


def narrow_studies() -> pd.DataFrame:
    return pd.DataFrame({"study": ["Andersen 2019", "Baker 2020", "Chen 2021", "Diaz 2022", "Evans 2023"],
                         "est": [0.72, 0.85, 0.64, 0.91, 0.78], "low": [0.55, 0.62, 0.45, 0.70, 0.60],
                         "high": [0.94, 1.16, 0.91, 1.18, 1.01], "w": [22.0, 18, 15, 25, 20]})


def test_a_forest_in_one_column_puts_its_columns_under_each_study(tmp_path, monkeypatch):
    """At 75 mm the effect and weight columns left 1 pt for the intervals; they move under the study label."""
    host_width(tmp_path, monkeypatch, width_mm=75)
    hl.use(brand=False)
    figure = hl.forest(narrow_studies(), "study", "est", "low", "high", weight="w")
    texts = {shape["text"]: shape for shape in figure.shapes if shape["kind"] == "text"}
    study, effect = texts["Andersen 2019"], texts["0.72 [0.55; 0.94]"]
    assert effect["y"] > study["y"] and effect["x"] < figure.plot_boxes[0].x + figure.plot_boxes[0].width / 2
    ticks = [shape["x"] for shape in figure.shapes if shape.get("part") == "tick"]
    assert ticks[-1] - ticks[0] >= load_tokens()["forest"]["min_plot"] * figure.settings.base_size
    wide = hl.forest(narrow_studies(), "study", "est", "low", "high", weight="w", size="onehalf")
    assert wide.figure.get_size_inches()[0] * 25.4 == pytest.approx(75)


def test_a_survival_plot_in_one_column_grows_taller_instead_of_failing(tmp_path, monkeypatch):
    """At 75 mm the at-risk table left the curves -7 pt; the figure grows until the plot keeps 8 x the base."""
    generator = np.random.default_rng(7)
    data = pd.DataFrame({"arm": generator.choice(["Control", "Low dose", "High dose"], 150),
                         "months": generator.exponential(20, 150).round(1) + 0.1,
                         "died": generator.integers(0, 2, 150)})
    hl.use(brand=False)
    wide = hl.kaplan_meier(data, "months", "died", "arm")
    assert wide.figure.get_size_inches()[1] * 25.4 == pytest.approx(84, abs=0.1)
    host_width(tmp_path, monkeypatch, width_mm=75)
    narrow = hl.kaplan_meier(data, "months", "died", "arm")
    narrow.figure.savefig(io.BytesIO(), format="png", dpi=30)
    least = load_tokens()["survival"]["min_plot"] * narrow.settings.base_size
    assert narrow.plot_boxes[0].height == pytest.approx(least, abs=0.5)
    assert narrow.figure.get_size_inches()[1] * 25.4 > 75 * 0.7


LONG_LABEL = "An exceptionally long category label that keeps going for seventy chars"


def drawn_extent(figure) -> tuple[float, float, float, float, float, float]:
    """Left, top, right and bottom of every drawn shape (texts by their measured width), and the figure's size."""
    from hairline.drawing import measure_for
    measure, xs, ys = measure_for(figure.settings), [], []
    for shape in figure.shapes:
        if shape["kind"] == "text":
            width = measure(shape["text"], shape["role"], shape.get("weight"))
            left = shape["x"] - {"left": 0.0, "center": width / 2, "right": width}[shape["align"]]
            xs += [left, left + width]
            ys.append(shape["y"])
        else:
            xs += [point[0] for point in shape["points"]]
            ys += [point[1] for point in shape["points"]]
    width, height = figure.figure.get_size_inches() * 72
    return min(xs), min(ys), max(xs), max(ys), width, height


def long_label_charts() -> dict:
    single = pd.DataFrame({"name": [LONG_LABEL, "Home", "Rehab", "Care home"], "n": [40, 30, 20, 10]})
    referrals = pd.DataFrame({"origin": [LONG_LABEL, "ED", "Ward"], "destination": ["ICU", "Ward", LONG_LABEL],
                              "patients": [4, 5, 6]})
    judged = pd.DataFrame({"study": list("ABC"), LONG_LABEL: ["Low", "High", "Low"], "Missing": ["Low", "Low", "Some"]})
    trials = pd.DataFrame({"study": ["A", "B"], "est": [0.8, 1.2], "low": [0.6, 0.9], "high": [1.1, 1.5]})
    flows = pd.DataFrame({"a": ["Salary", "Salary", "Benefits"], "b": ["Rent", LONG_LABEL, "Food"], "v": [5, 3, 2]})
    return {
        "donut": lambda: hl.donut(single, "name", "n"),
        "chord": lambda: hl.chord(referrals, "origin", "destination", "patients"),
        "venn": lambda: hl.venn({LONG_LABEL: [1, 2, 3], "Hypertension": [2, 3, 4]}),
        "risk of bias": lambda: hl.risk_of_bias(judged, "study", domains=[LONG_LABEL, "Missing"],
                                                overall="Overall judgement across every domain of the tool"),
        "forest": lambda: hl.forest(trials, "study", "est", "low", "high",
                                    favours=["Favours the experimental treatment arm strongly",
                                             "Favours the control arm of the randomised trial"]),
        "sankey": lambda: hl.sankey(flows, ["a", "b"], "v"),
    }


@pytest.mark.parametrize("width_mm", [120, 75])
@pytest.mark.parametrize("chart", list(long_label_charts()))
def test_long_labels_wrap_inside_the_figure(chart, width_mm, tmp_path, monkeypatch):
    """A 70-character label ran off the figure (a donut label to 411 pt of 340, sankey links from x = -152); it
    wraps into the room the chart's minimum size leaves, and the figure grows when the lines need the height."""
    host_width(tmp_path, monkeypatch, width_mm=width_mm)
    hl.use(brand=False)
    figure = long_label_charts()[chart]()
    left, top, right, bottom, width, height = drawn_extent(figure)
    assert 0 <= left and right <= width + 0.01 and 0 <= top and bottom <= height
    assert LONG_LABEL not in [shape["text"] for shape in figure.shapes if shape["kind"] == "text"]


def test_a_word_wider_than_the_room_names_the_room_it_needs(tmp_path, monkeypatch):
    host_width(tmp_path, monkeypatch, width_mm=45)
    hl.use(brand=False)
    single = pd.DataFrame({"name": ["Supercalifragilisticexpialidocious", "Home"], "n": [3, 1]})
    with pytest.raises(hl.HairlineLayoutError, match=r"donut: the label 'Supercalifragilisticexpialidocious' needs "
                                                     r"\d+ pt, but the figure leaves \d+ pt"):
        hl.donut(single, "name", "n", size="onehalf")
    hl.use(brand=False)
    with pytest.raises(hl.HairlineLayoutError, match=r"total_label .* does not fit the hole"):
        hl.donut(single.assign(name=["A", "B"]), "name", "n", labels="ring",
                 total_label="Supercalifragilisticexpialidocious")


def test_a_label_as_wide_as_its_room_keeps_one_line():
    from hairline.charts.wrapping import fit_lines, pair_lines

    def measure(text, role="label", weight=None):
        return 0.1 * len(text) + 0.2

    assert fit_lines("Care home", measure("Care home") + 0.3 + 0.4, measure, "donut", "the label", 0.4,
                     0.3) == ["Care home"]
    assert pair_lines("Care home", measure("home") + 0.05, measure, 0.4, 0.3) == ["Care", "home", ""]


def test_a_sankey_with_many_nodes_grows_instead_of_losing_them():
    """40 sources at 120 mm: a node sat above the panel and labels collided (shapes to y = 306 of 238 pt)."""
    hl.use(brand=False)
    data = pd.DataFrame({"a": [f"Source {index}" for index in range(40) for _ in range(3)], "b": ["X", "Y", "Z"] * 40,
                         "v": [1 + index % 5 for index in range(120)]})
    figure = hl.sankey(data, ["a", "b"], "v")
    left, top, right, bottom, width, height = drawn_extent(figure)
    assert top >= figure.plot_boxes[0].y - 0.01 and bottom <= height and height > 238
    nodes = sorted((shape["points"][0][1], shape["points"][2][1]) for shape in figure.shapes
                   if shape.get("role") == "node" and shape["points"][0][0] < width / 2)
    assert len(nodes) == 40 and all(upper[1] < lower[0] for upper, lower in zip(nodes, nodes[1:], strict=False))
    baselines = sorted(shape["y"] for shape in figure.shapes if shape["kind"] == "text"
                       and shape["text"].startswith("Source"))
    line = figure.settings.base_size * load_tokens()["type"]["roles"]["label"]["factor"]
    assert min(b - a for a, b in zip(baselines, baselines[1:], strict=False)) >= line


def test_a_nested_donut_key_with_many_rows_grows_the_figure():
    """80 children started the key at y = -455 pt; the key now starts in the panel and the figure grows."""
    hl.use(brand=False)
    data = pd.DataFrame({"p": [f"Parent {index // 20}" for index in range(80)],
                         "c": [f"Child {index}" for index in range(80)], "n": [1 + index % 7 for index in range(80)]})
    figure = hl.donut(data, levels=["p", "c"])
    left, top, right, bottom, width, height = drawn_extent(figure)
    assert top >= figure.plot_boxes[0].y - 0.01 and bottom <= height and right <= width


def flat_points(shapes: list[dict]) -> list[float]:
    return [value for shape in shapes for value in ([shape["x"], shape["y"]] if shape["kind"] == "text" else
                                                    [number for point in shape["points"] for number in point])]


def test_wrapped_labels_match_the_shared_fixture():
    from hairline.charts.chord_geometry import chord_drawing
    from hairline.charts.donut_geometry import donut_drawing
    from hairline.charts.forest_geometry import forest_drawing
    from hairline.charts.risk_of_bias_geometry import risk_of_bias_drawing
    from hairline.charts.sankey_geometry import sankey_drawing
    from hairline.charts.venn_geometry import venn_drawing
    from hairline.charts.wrapping import spread_blocks
    from hairline.layout.geometry import Box
    fixture = json.loads((Path(__file__).parent / "fixtures" / "wrapping.json").read_text())
    style = fixture["style"]
    drawings = {"donut": donut_drawing, "chord": chord_drawing, "venn": venn_drawing,
                "risk_of_bias": risk_of_bias_drawing, "forest": forest_drawing, "sankey": sankey_drawing}

    def measure(text, role, weight=None):
        return 0.5 * style["sizes"][role] * len(text)
    for case in fixture["cases"]:
        box = Box(*case["box"])
        if "error" in case:
            with pytest.raises(hl.HairlineLayoutError) as error:
                drawings[case["chart"]](case["spec"], box, measure, style)
            assert str(error.value) == case["error"]
        else:
            shapes = drawings[case["chart"]](case["spec"], box, measure, style)
            assert [shape.get("text") for shape in shapes] == [shape.get("text") for shape in case["shapes"]]
            assert flat_points(shapes) == pytest.approx(flat_points(case["shapes"]))
    for case in fixture["blocks"]:
        assert spread_blocks(case["positions"], case["heights"], case["top"], case["bottom"]) == \
            pytest.approx(case["centres"])


# Deferred findings of the 0.2.0 stress test.

def many_groups(groups: int = 10, sites: int = 12) -> pd.DataFrame:
    rng = np.random.default_rng(1)
    return pd.DataFrame({"arm": [f"G{index % groups}" for index in range(400)], "age": rng.normal(60, 10, 400),
                         "site": [f"S{index % sites}" for index in range(400)],
                         "time": rng.exponential(10, 400), "event": rng.integers(0, 2, 400)})


@pytest.mark.parametrize("endpoint", ["describe", "compare", "compare_site", "distribution", "survival"])
def test_study_endpoints_with_more_groups_than_colours_keep_table_values_and_text(endpoint):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        study = hl.study(many_groups(), group="arm", time="time", event="event", variables=["age", "site"],
                         units={"age": "years", "time": "months"})
    calls = {"describe": study.describe, "compare": lambda: study.compare("age"),
             "compare_site": lambda: study.compare("site"), "distribution": lambda: study.distribution("age"),
             "survival": study.survival}
    what = "12 categories of 'site'" if endpoint == "compare_site" else "10 groups"
    with pytest.warns(UserWarning, match=f"{what} need more colours than the 8 of palette 'daylight', so the "
                                         "result has no figure"):
        result = calls[endpoint]()
    assert result.figure is None and len(result.table) and result.values and result.text


def test_study_endpoints_draw_their_figure_within_the_palette():
    study = hl.study(many_groups(groups=8, sites=8), group="arm", variables=["age", "site"], units={"age": "years"})
    assert study.compare("site").figure is not None and study.describe().figure is not None


def reference_logrank_chisq(time, event, group) -> float:
    """The textbook loop over event times, for comparison with the counted version."""
    time, event, group = np.asarray(time, float), np.asarray(event, float), np.asarray(group)
    labels = list(dict.fromkeys(group))
    difference, variance = np.zeros(len(labels)), np.zeros((len(labels), len(labels)))
    for moment in np.unique(time[event == 1]):
        at_risk = np.array([((group == label) & (time >= moment)).sum() for label in labels], float)
        deaths = np.array([((group == label) & (time == moment) & (event == 1)).sum() for label in labels], float)
        n, d = at_risk.sum(), deaths.sum()
        share = at_risk / n
        difference += deaths - d * share
        if n > 1:
            variance += d * (n - d) / (n - 1) * (np.diag(share) - np.outer(share, share))
    return float(difference[1:] @ np.linalg.solve(variance[1:, 1:], difference[1:]))


def test_the_log_rank_test_counts_each_group_once_and_keeps_its_value():
    rng = np.random.default_rng(4)
    time, event = np.round(rng.exponential(10, 600), 1), rng.integers(0, 2, 600)
    group = rng.choice(["A", "B", "C"], 600)
    assert logrank(time, event, group)["chisq"] == pytest.approx(reference_logrank_chisq(time, event, group),
                                                                 rel=1e-12)
    time, event, group = rng.exponential(10, 100_000), rng.integers(0, 2, 100_000), rng.choice(["A", "B"], 100_000)
    assert np.isfinite(logrank(time, event, group)["chisq"])


@pytest.mark.parametrize(("scale", "expected"), [(1e-9, "0.0000000012"), (1e-11, "0.000000000012")])
def test_values_near_zero_keep_two_significant_digits(scale, expected):
    from hairline.numbers import auto_digits, snap_noise
    values = np.linspace(0.8, 1.6, 61) * scale
    assert format_number(snap_noise(np.median(values)), auto_digits(values)) == expected
    data = pd.DataFrame({"group": ["A"] * 61, "value": values})
    texts = [text.get_text() for text in hl.spread(data, "group", "value", stats=["median"]).figure.findobj(
        matplotlib.text.Text)]
    assert expected in texts and "0.000000" not in texts
    assert hl.study(data.assign(group=None), variables=["value"], units={"value": "mol"}).describe().table.iloc[
        1, 1].startswith(expected)


def test_ordinary_values_keep_their_decimals():
    from hairline.numbers import auto_digits
    assert [auto_digits([0.0004, 0.00041]), auto_digits([12.3, 14.1]), auto_digits([1000.2, 1000.4])] == [6, 1, 1]


def test_a_figure_that_cannot_be_laid_out_is_a_layout_error_from_save(tmp_path):
    figure = hl.figure("T", width_mm=60, height_mm=20, panels=3)
    with pytest.raises(hl.HairlineLayoutError, match="figure too small"):
        hl.save(figure, tmp_path / "small", formats=["png", "svg"], dpi=72)
    assert list(tmp_path.iterdir()) == []


def write_brand(tmp_path, text: str) -> Path:
    path = tmp_path / "_brand.yml"
    path.write_text('color:\n  palette:\n    harbor: "#0b3d6e"\n    poppy: "#f2545b"\n' + text)
    return path


@pytest.mark.parametrize(("text", "message"), [
    ("typography:\n  fonts: nope\n", "typography.fonts[0]: must be a mapping with family and source; got 'nope'"),
    ("defaults:\n  hairline:\n    colors: [harbor]\n", "defaults.hairline.colors: must map entity names"),
    ("defaults:\n  hairline:\n    sizes: [1, 2]\n", "defaults.hairline.sizes: must map text roles to sizes in pt"),
    ("defaults:\n  hairline:\n    outputs: [pdf]\n", "defaults.hairline.outputs: must map export types"),
    ("defaults:\n  hairline:\n    groups: harbor\n", "defaults.hairline.groups: must map group names"),
    ("defaults: yes\n", "defaults: must map tools to their settings"),
    ("meta: Example\n", "meta: must map its details"),
])
def test_brand_sections_in_the_wrong_shape_name_the_key(tmp_path, text, message):
    with pytest.raises(ValueError, match=re.escape(message)):
        hl.use(brand=write_brand(tmp_path, text))


def test_a_brand_palette_given_as_a_list_is_refused(tmp_path):
    path = tmp_path / "_brand.yml"
    path.write_text('color:\n  palette: ["#0b3d6e", "#f2545b"]\n')
    with pytest.raises(ValueError, match=re.escape("color.palette: must map colour names to hex values")):
        hl.use(brand=path)


def test_a_brand_list_may_be_written_as_its_single_value(tmp_path):
    brand = hl.load_brand(write_brand(tmp_path, "defaults:\n  hairline:\n    categorical: harbor\n"))
    assert brand.names == ["harbor"] and brand.colors_given == ["#0b3d6e"]


def test_a_brand_key_given_twice_is_refused(tmp_path):
    path = tmp_path / "_brand.yml"
    path.write_text('color:\n  palette:\n    harbor: "#0b3d6e"\n    harbor: "#f2545b"\n')
    with pytest.raises(ValueError, match=re.escape("_brand.yml: line 4: key 'harbor' is given twice")):
        hl.load_brand(path)


def test_a_dpi_too_low_for_text_is_refused(tmp_path):
    with pytest.raises(ValueError, match="dpi must be at least 20, below which text is smaller than a pixel"):
        hl.save(hl.figure("T"), tmp_path / "low", formats=["png"], dpi=1)


def test_a_bar_without_a_value_has_no_bar_label_or_tooltip():
    data = pd.DataFrame({"name": ["Alpha", "Beta", "Gamma", "Delta"], "value": [3.0, 5.5, np.nan, 2.0]})
    figure = hl.bars(data, "name", "value", sort="given")
    tips = [tip["text"] for series in figure_targets(figure)["series"] for tip in series["tips"]]
    assert [tip.split(": ")[-1] for tip in tips] == ["Alpha, 3.0", "Beta, 5.5", "Delta, 2.0"]
    assert [text.get_text() for text in figure.ax.texts] == ["3.0", "5.5", "2.0"]
    grouped = pd.DataFrame({"name": ["A", "A", "B", "B"], "g": ["x", "y", "x", "y"], "value": [3.0, np.nan, 2.0, 1.0]})
    stacked = hl.bars(grouped, "name", "value", by="g", stacked=True)
    assert [text.get_text() for text in stacked.ax.texts] == ["3", "2", "1", "3", "3"]


def test_study_texts_count_one_row_in_the_singular():
    data = pd.DataFrame({"arm": ["A"], "age": [61.5]})
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        study = hl.study(data, group="arm", units={"age": "years"})
    assert study.describe().text.startswith("1 participant: 1 in A.")
    assert str(study).startswith("Study of 1 participant: group = arm; 1 variable")
    assert "group 'A' has 1 row" in str(study)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mice = hl.study(pd.DataFrame({"weight": [21.5, 23.0, np.nan]}), units={"weight": "g"},
                        unit=("mouse", "mice"))
    assert mice.describe().text.startswith("3 mice.")
    assert hl.study(pd.DataFrame({"weight": [21.5]}), unit=("mouse", "mice")).describe().text == "1 mouse."
    with pytest.raises(ValueError, match="unit must be a plural noun"):
        hl.study(data, unit=3)


def test_an_unknown_output_is_refused_without_a_brand():
    with pytest.raises(ValueError, match="output 'epub' must be one of screen, pdf, html, docx"):
        hl.use(output="epub", brand=False)
