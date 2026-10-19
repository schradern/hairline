import json

import matplotlib.pyplot as plt
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
