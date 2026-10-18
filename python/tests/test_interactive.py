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
