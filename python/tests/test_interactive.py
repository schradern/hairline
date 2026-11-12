import json
import runpy
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import hairline as hl
from hairline.interactive import figure_targets


def targets_of(path):
    html = path.read_text(encoding="utf-8")
    start = html.index('class="hairline-targets">') + len('class="hairline-targets">')
    return html, json.loads(html[start:html.index("</script>", start)])


def test_html_export_holds_the_svg_targets_script_and_font(tmp_path):
    hl.use(brand=False)
    figure = hl.figure("Two series", size="onehalf")
    figure.ax.plot([0, 1, 2], [1, 3, 2], label="North")
    figure.ax.plot([0, 1, 2], [2, 1, 3], label="South")
    figure.legend()
    path = hl.save(figure, tmp_path / "lines", formats=("html",))[0]
    html, targets = targets_of(path)
    assert html.startswith("<!doctype html>") and "<svg" in html and "@font-face" in html
    assert [series["name"] for series in targets["series"]] == ["North", "South"]
    assert targets["series"][0]["tips"][1]["text"] == "North: 1, 3"
    assert [entry["name"] for entry in targets["legend"]] == ["North", "South"]


def test_fit_lines_stay_static_and_points_are_targets():
    data = pd.DataFrame({"x": [1, 2, 3, 4, 5, 6], "y": [1.0, 2.2, 2.9, 4.1, 5.2, 5.8]})
    targets = figure_targets(hl.scatter(data, "x", "y", fit="linear"))
    assert len(targets["series"]) == 1 and len(targets["series"][0]["tips"]) == 6


def test_html_needs_a_hairline_figure(tmp_path):
    figure, _ = plt.subplots()
    with pytest.raises(RuntimeError, match="html export needs a figure made with hairline"):
        hl.save(figure, tmp_path / "plain", formats=("html",))


def test_html_figure_is_named_by_title_and_subtitle(tmp_path):
    hl.use(brand=False)
    figure = hl.figure("Two series", subtitle="Weekly <counts>", size="onehalf")
    figure.ax.plot([0, 1, 2], [1, 3, 2], label="North")
    html, _ = targets_of(hl.save(figure, tmp_path / "named", formats=("html",))[0])
    assert 'aria-label="Two series. Weekly &lt;counts>"' in html


def power_curve(digits=None):
    hl.use(brand=False)
    figure = hl.figure("Power by sample size", size="onehalf")
    figure.ax.plot([40, 80, 120, 160], [0.05, 0.42, 0.896, 1.0], label="Power")
    if digits is None:
        figure.percent_axis(0)
    else:
        figure.percent_axis(0, digits=digits)
    return figure


def test_percent_axis_digits_reach_the_tooltips():
    tips = figure_targets(power_curve(digits=1))["series"][0]["tips"]
    assert [tip["text"] for tip in tips] == ["Power: 40, 5.0%", "Power: 80, 42.0%", "Power: 120, 89.6%",
                                             "Power: 160, 100.0%"]


def test_tooltip_digits_default_to_the_shared_rule():
    tips = figure_targets(power_curve())["series"][0]["tips"]
    assert tips[2]["text"] == "Power: 120, 90%"


def test_axis_digits_leave_the_ticks_alone():
    def tick_texts(figure):
        figure.figure.canvas.draw()
        return [label.get_text() for label in figure.ax.get_yticklabels()]
    assert tick_texts(power_curve(digits=1)) == tick_texts(power_curve())


def test_number_axis_digits_reach_the_tooltips_on_either_axis():
    hl.use(brand=False)
    figure = hl.figure("Dose and response", size="onehalf")
    figure.ax.plot([0.5, 1.25, 2.0], [1.5, 2.25, 3.125], label="Response")
    figure.number_axis(0, digits=2)
    figure.number_axis(0, which="x", digits=0)
    tips = figure_targets(figure)["series"][0]["tips"]
    assert [tip["text"] for tip in tips] == ["Response: 1, 1.50", "Response: 1, 2.25", "Response: 2, 3.13"]


def test_number_axis_turns_a_percent_axis_back_into_numbers():
    figure = power_curve(digits=1)
    figure.number_axis(0, digits=2)
    assert figure_targets(figure)["series"][0]["tips"][2]["text"] == "Power: 120, 0.90"


@pytest.mark.parametrize("digits", [-1, 1.5, "1", True])
def test_axis_digits_must_be_a_whole_number_from_zero(digits):
    figure = hl.figure("Power by sample size", size="onehalf")
    with pytest.raises(ValueError, match="digits must be a whole number from 0 to 10"):
        figure.percent_axis(0, digits=digits)


GALLERY = Path(__file__).resolve().parents[2] / "gallery" / "python"
SCRIPTS = sorted(path.stem for path in GALLERY.glob("*.py") if path.stem != "common")
# Its HTML export is a real <table>, read as text: it has no marks to hover.
WITHOUT_TIPS = {"table_characteristics"}


def gallery_figures(name, monkeypatch):
    """The figures a gallery script makes, collected where it would save them."""
    monkeypatch.syspath_prepend(str(GALLERY))
    import common
    found = []
    monkeypatch.setattr(common, "finish", lambda figure, *_: found.append(figure))
    runpy.run_path(str(GALLERY / f"{name}.py"), run_name="__main__")
    return found


def untipped(figure):
    """The series a figure exports without a tooltip, or ['no series'] when it exports none."""
    series = figure_targets(figure)["series"]
    return [entry["name"] for entry in series if not entry["tips"]] if series else ["no series"]


@pytest.mark.skipif(not SCRIPTS, reason="the census runs the gallery scripts of the repository")
@pytest.mark.parametrize("name", SCRIPTS)
def test_every_gallery_figure_exports_a_tooltip_per_series(name, monkeypatch):
    figures = gallery_figures(name, monkeypatch)
    assert figures, f"{name} made no figure"
    for figure in figures:
        if name in WITHOUT_TIPS:
            assert not figure_targets(figure)["series"]
        else:
            assert untipped(figure) == [], name


@pytest.mark.skipif(not SCRIPTS, reason="the census runs the gallery scripts of the repository")
def test_every_chart_has_a_gallery_figure_so_the_census_reaches_it():
    charts = {name for name, module in hl.LAZY_NAMES.items() if module.startswith("hairline.charts.")}
    scripts = " ".join(path.read_text(encoding="utf-8") for path in GALLERY.glob("*.py"))
    assert sorted(name for name in charts if f"hl.{name}(" not in scripts) == []


def cohort(count=40):
    generator = np.random.default_rng(3)
    return pd.DataFrame({"arm": ["Standard"] * (count // 2) + ["Early"] * (count // 2),
                         "age": np.round(generator.normal(64, 10, count)), "sex": generator.choice(["F", "M"], count),
                         "months": np.round(generator.exponential(12, count), 1),
                         "died": generator.integers(0, 2, count),
                         "date": pd.date_range("2025-01-01", periods=count).strftime("%Y-%m-%d")})


def test_study_figures_export_a_tooltip_per_group():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        study = hl.study(cohort(), group="arm", time="months", event="died", variables=["age", "sex"])
        table = pd.DataFrame({"study": ["age"], "estimate": [1.2], "low": [1.0], "high": [1.5]})
        results = [study.describe(), study.distribution("age"), study.compare("age"), study.compare("sex"),
                   study.survival(), study.over_time("date", "age"), study.effects(table, measure="OR")]
    for result in results:
        assert untipped(result.figure) == []
    names = {entry["name"] for entry in figure_targets(results[0].figure)["series"]}
    assert names == {"Standard", "Early"}


def stays(count=24):
    generator = np.random.default_rng(11)
    return pd.DataFrame({"unit": np.repeat(["Surgical", "Medical", "Neuro"], count),
                         "year": np.tile(["2024", "2025"], count * 3 // 2),
                         "days": np.round(generator.gamma(3, 2, count * 3), 1)})


def series_of(figure):
    return {entry["name"]: entry for entry in figure_targets(figure)["series"]}


def test_raincloud_summary_tip_reads_as_the_numbers_under_the_groups():
    figure = hl.raincloud(stays(), "unit", "days", summary=("median", "mean", "iqr"), stats=("median", "ci"),
                          compare="Surgical")
    series = series_of(figure)
    assert list(series) == ["Surgical", "Medical", "Neuro"]
    rows = figure.table_spec["rows"]
    for position, name in enumerate(series):
        summary = series[name]["tips"][0]["text"]
        assert summary.startswith(f"{name}: Median ")
        for label, _, texts in rows:
            label = label or "n ="
            value = texts[position][1].removeprefix("n = ")
            assert f"{label.removesuffix(' =')} {value}" in summary
    assert "Δ Reference, p –" in series["Surgical"]["tips"][0]["text"]
    assert series["Medical"]["tips"][1]["text"].startswith("Medical: ")


def test_raincloud_points_tip_their_value_and_clipped_ones_none():
    data = stays()
    data.loc[0, "days"] = 400.0
    figure = hl.raincloud(data, "unit", "days", clip=(None, 100))
    surgical = series_of(figure)["Surgical"]
    values = [tip["text"].split(": ", 1)[1] for tip in surgical["tips"][1:]]
    assert len(values) == 23 and "400.0" not in values and "n 24" in surgical["tips"][0]["text"]


def test_raincloud_targets_follow_facet_panels_and_leave_small_groups_out():
    data = pd.concat([stays(), pd.DataFrame({"unit": ["Burns"] * 2, "year": ["2025"] * 2, "days": [3.0, 4.0]})])
    figure = hl.raincloud(data, "unit", "days", facet="year", min_n=5)
    series = series_of(figure)
    assert sorted(series) == ["Medical", "Neuro", "Surgical"]
    summaries = [tip for tip in series["Neuro"]["tips"] if ", n " in tip["text"]]
    assert [tip["text"].rsplit(", n ", 1)[1] for tip in summaries] == ["12", "12"]


def test_tooltips_follow_the_figure_locale():
    hl.use(locale="de")
    figure = hl.raincloud(stays(), "unit", "days", summary=("mean", "ci"))
    tips = [tip["text"] for tip in series_of(figure)["Surgical"]["tips"]]
    assert "95 %-KI" in tips[0] and "," in tips[0].split("Mittelwert ", 1)[1].split(" ", 1)[0]
    assert all("." not in tip.split(": ", 1)[1] for tip in tips[1:])


def test_ridgeline_tip_reads_as_its_numbers_column():
    figure = hl.ridgeline(stays(), "unit", "days", stats=("median", "iqr"), compare="adjacent")
    series = series_of(figure)
    assert list(series) == ["Surgical", "Medical", "Neuro"]
    for index, (name, entry) in enumerate(series.items()):
        (tip,) = entry["tips"]
        beside = [f"{label} {value}" for position, label, value in figure.side_numbers[0]
                  if position == len(series) - 1 - index]
        assert len(beside) == 4 and tip["text"] == f"{name}: " + ", ".join([*beside[:2], "n 24", *beside[2:]])
    assert series["Surgical"]["tips"][0]["text"].endswith("Δ –, p –")


def test_ridgeline_targets_follow_facet_panels_clip_and_min_n():
    data = pd.concat([stays(), pd.DataFrame({"unit": ["Burns"] * 2, "year": ["2025"] * 2, "days": [3.0, 4.0]})])
    figure = hl.ridgeline(data, "unit", "days", facet="year", min_n=5, clip=(None, 100))
    series = series_of(figure)
    assert sorted(series) == ["Medical", "Neuro", "Surgical"]
    assert [tip["text"].rsplit(", n ", 1)[1] for tip in series["Surgical"]["tips"]] == ["12", "12"]


def test_prisma_boxes_tip_their_counts_and_reasons_without_covering_their_text():
    figure = hl.prisma({"identified": 120, "duplicates": 20, "screened": 100, "excluded": 70, "assessed": 30,
                        "excluded_reasons": {"Wrong population": 8, "No control": 4}, "included": 18})
    series = series_of(figure)
    assert series["Reports excluded"]["tips"][0]["text"] == \
        "Reports excluded:\nWrong population (n = 8)\nNo control (n = 4)"
    assert "Records screened (n = 100)" in series
    assert all(mark.get("hit") for entry in series.values() for mark in entry["marks"])
