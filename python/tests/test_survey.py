"""Charts for surveys: diverging bars for rating scales, spread rows in sections with the mean, and the bar options
for multiple choice, context categories, an n column and answers named inside."""

import matplotlib.colors as mcolors
import pandas as pd
import pytest

import hairline as hl
from hairline.charts.likert import likert_spec, scale_bins
from hairline.charts.likert_geometry import likert_drawing, segments
from hairline.charts.spread import spread_spec
from hairline.charts.spread_geometry import spread_drawing
from hairline.interactive import figure_targets
from hairline.layout.geometry import Box
from hairline.palettes import default_ramp, interpolate, ramp

STYLE = {"base": 9.0, "sizes": {"title": 13.5, "panel": 9.0, "label": 7.2, "caption": 7.2}, "line_gap": 0.25,
         "cap_height": 0.7, "descender": 0.21, "leader_width": 0.54, "data_width": 1.26, "axis_width": 0.585,
         "grid": 0.45, "neutral": {"ink": "#1b1e22", "muted": "#5b6168", "faint": "#6f757d", "axis": "#c4c8cd",
                                   "surface": "#ffffff", "band": "#f2f3f5", "grid": "#eef0f2"}}


def measure(text: str, role: str, weight: int | None = None) -> float:
    return 0.5 * STYLE["sizes"][role] * len(text)


def ratings() -> pd.DataFrame:
    """Two statements on a ten-point scale, the second worded negatively, in two sections."""
    rows = [("A", "Clear", rating) for rating in (1, 3, 6, 7, 8, 9, 10, 10)]
    rows += [("B", "Rushed", rating) for rating in (1, 1, 2, 2, 3, 6, 9, 10)]
    return pd.DataFrame(rows, columns=["section", "statement", "rating"])


def test_a_ten_point_scale_reads_in_four_bins_with_agreement_cool():
    bins = scale_bins([float(level) for level in range(1, 11)], None, None)
    assert [entry["name"] for entry in bins] == ["1–2", "3–5", "6–8", "9–10"]
    assert [entry["side"] for entry in bins] == ["left", "left", "right", "right"]
    colors = list(reversed(interpolate(ramp(default_ramp("diverging")), 5)))
    assert [entry["color"] for entry in bins] == [colors[0], colors[1], colors[3], colors[4]]


def test_an_odd_scale_centres_its_middle_level_and_bins_can_be_named():
    bins = scale_bins([1.0, 2.0, 3.0, 4.0, 5.0], None, None)
    assert [(entry["name"], entry["side"]) for entry in bins] == [("1", "left"), ("2", "left"), ("3", "middle"),
                                                                 ("4", "right"), ("5", "right")]
    named = scale_bins([float(level) for level in range(1, 11)], None, {"low": (1, 5), "high": (6, 10)})
    assert [entry["name"] for entry in named] == ["low", "high"]
    with pytest.raises(ValueError, match="bin 'across' must hold levels of one side"):
        scale_bins([float(level) for level in range(1, 11)], None, {"across": (4, 7), "rest": (1, 3)})


def test_reversed_items_are_recoded_and_marked_and_rows_carry_their_numbers():
    hl.use(brand=False)
    spec = likert_spec(ratings(), "statement", "rating", levels=range(1, 11), group="section", reverse=["Rushed"])
    rushed = spec["rows"][1]
    assert rushed["name"] == "Rushed (reversed)"
    assert rushed["shares"] == pytest.approx([25.0, 12.5, 12.5, 50.0])
    # Recoded 10 10 9 9 8 5 2 1: on the data's levels the median is the 4th of 8 values, the quartiles the 2nd and 6th.
    assert rushed["pairs"] == [["Median", "8"], ["IQR", "2–9"], ["n", "8"]]
    with pytest.raises(ValueError, match="reverse names 'Missing'"):
        likert_spec(ratings(), "statement", "rating", reverse=["Missing"])


def test_bins_stack_outward_from_the_split_and_sections_get_headings():
    hl.use(brand=False)
    spec = likert_spec(ratings(), "statement", "rating", levels=range(1, 11), group="section")
    spans = {entry["name"]: (low, high) for entry, low, high, _ in segments(spec["rows"][0], spec["bins"])}
    assert spans["3–5"] == (pytest.approx(-12.5), 0.0) and spans["1–2"] == (pytest.approx(-25.0), pytest.approx(-12.5))
    shapes = likert_drawing(spec, Box(0, 0, 600, 200), measure, STYLE)
    headings = [shape["text"] for shape in shapes if shape.get("part") == "heading"]
    assert headings == ["A", "B"]
    tips = [shape["tip"] for shape in shapes if "tip" in shape]
    assert "Clear: 9–10, 38%" in tips
    assert spec["axis"]["low"] == -spec["axis"]["high"]


def test_likert_puts_its_bins_in_the_legend_row_and_its_segments_in_the_tooltips():
    hl.use(brand=False)
    figure = hl.likert(ratings(), "statement", "rating", levels=range(1, 11), key_title="Rating")
    figure.figure.canvas.draw()
    assert figure.layout_report()["legend_labels"] == ["Rating", "1–2", "3–5", "6–8", "9–10"]
    names = {series["name"] for series in figure_targets(figure)["series"]}
    assert {"1–2", "9–10"} <= names


def importance() -> pd.DataFrame:
    rows = [("Booking", "Online", value) for value in (9, 10, 9, 8)] + \
        [("Booking", "Phone", value) for value in (3, 5, 4, 6)] + \
        [("Records", "Results", value) for value in (9, 8, 10, 9)]
    return pd.DataFrame(rows, columns=["area", "feature", "rating"])


def test_spread_sections_are_lettered_sorted_and_marked_with_the_mean():
    hl.use(brand=False)
    spec = spread_spec(importance(), "feature", "rating", section="area", panel_letters=True, mean=True,
                       sort="median", stats=("median", "n"), color_by="area")
    assert [row["name"] for row in spec["rows"]] == ["Online", "Phone", "Results"]
    assert spec["rows"][0]["mean"] == pytest.approx(9.0)
    assert [label for _, _, label in spec["legend"]][-2:] == ["Median", "Mean"]
    shapes = spread_drawing(spec, Box(0, 0, 600, 200), measure, STYLE)
    assert [shape["text"] for shape in shapes if shape.get("part") == "letter"] == ["a", "b"]
    assert sum(shape.get("role") == "mean" for shape in shapes) == 3
    with pytest.raises(ValueError, match="sort 'mean' must be 'median'"):
        spread_spec(importance(), "feature", "rating", sort="mean")


def sources() -> pd.DataFrame:
    rows = [(1, "Sources", "Website"), (1, "Sources", "Leaflet"), (2, "Sources", "Website"), (3, "Sources", "None"),
            (1, "Topics", "Diet"), (2, "Topics", "Costs")]
    return pd.DataFrame(rows, columns=["respondent", "question", "answer"])


def test_multiple_choice_counts_respondents_and_greys_the_exclusive_answer():
    hl.use(brand=False)
    figure = hl.bars(sources(), "answer", facet="question", respondents="respondent", context=["None"], header="n",
                     horizontal=True, size="double")
    figure.figure.canvas.draw()
    heights = {patch.get_y(): patch.get_width() for patch in figure.axes[0].patches}
    assert sorted(heights.values()) == pytest.approx([1 / 3, 1 / 3, 2 / 3])
    colors = [mcolors.to_hex(patch.get_facecolor()) for patch in figure.axes[0].patches]
    assert colors[-1] != colors[0]
    assert figure.category_axes[(0, "y")][0] == "None"
    assert dict(figure.headers[0].stats) == {"n": "3"}
    assert figure.caption == "Several answers were possible."
    with pytest.raises(ValueError, match="respondents counts one answer per row"):
        hl.bars(sources(), "answer", "respondent", respondents="respondent")


def answers() -> pd.DataFrame:
    rows = [("Recommend", "Yes", 30), ("Recommend", "No", 70), ("Reminder", "Text", 55), ("Reminder", "Email", 45)]
    return pd.DataFrame(rows, columns=["question", "answer", "count"])


def test_answers_named_inside_with_an_n_column():
    hl.use(brand=False)
    figure = hl.bars(answers(), "question", "count", by="answer", stacked=True, percent=True, sort="given",
                     inside="name", show_n="column", size="double")
    figure.figure.canvas.draw()
    assert figure.side_numbers[0] == [(1.0, "n", "100"), (0.0, "n", "100")]
    texts = sorted(artist.get_text() for _, artist, _, _ in figure.inside_labels)
    assert texts == ["Email 45%", "No 70%", "Text 55%", "Yes 30%"]
    names = {series["name"] for series in figure_targets(figure)["series"]}
    assert names == {"Yes", "No", "Text", "Email"}
    plain = hl.bars(answers(), "question", "count", by="answer", stacked=True, percent=True, size="double")
    plain.figure.canvas.draw()
    assert figure.plot_boxes[0].width < plain.plot_boxes[0].width
    with pytest.raises(ValueError, match="need horizontal bars"):
        hl.bars(answers(), "question", "count", show_n="column", horizontal=False)


def test_legend_ramp_takes_names_and_the_legend_an_open_diamond():
    hl.use(brand=False)
    figure = hl.figure("Key", size="double")
    figure.legend([("diamond", "#1b1e22", "Mean")])
    figure.legend_ramp(["#111111", "#555555"], [0.5, 1.0], "Rating", labels=["low", "high"])
    figure.figure.canvas.draw()
    assert figure.layout_report()["legend_labels"] == ["Mean", "Rating", "low", "high"]
    with pytest.raises(ValueError, match="labels gives 1 names for 2 steps"):
        figure.legend_ramp(["#111111", "#555555"], [0.5, 1.0], labels=["one"])
