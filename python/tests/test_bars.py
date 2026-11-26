import matplotlib.colors as mcolors
import pandas as pd
import pytest

import hairline as hl


def admissions():
    return pd.DataFrame({"diagnosis": ["Sepsis"] * 6 + ["Trauma"] * 3 + ["Pneumonia"] * 8 + ["Stroke"] * 2,
                         "sex": (["f", "m"] * 10)[:19]})


def bar_heights(figure):
    return [patch.get_height() for patch in figure.ax.patches]


def test_raw_rows_are_counted_and_sorted_by_value():
    figure = hl.bars(admissions(), "diagnosis")
    figure.figure.canvas.draw()
    assert bar_heights(figure) == [8, 6, 3, 2]
    assert [label.get_text() for label in figure.ax.get_xticklabels()] == ["Pneumonia", "Sepsis", "Trauma", "Stroke"]
    assert figure.title == "Count by diagnosis"


def test_values_are_labelled_at_the_bar_ends():
    figure = hl.bars(admissions(), "diagnosis")
    assert sorted(text.get_text() for text in figure.ax.texts) == ["2", "3", "6", "8"]


def test_groups_side_by_side_get_a_legend():
    figure = hl.bars(admissions(), "diagnosis", by="sex")
    figure.figure.canvas.draw()
    assert figure.layout_report()["legend_labels"] == ["f", "m"]
    assert len(figure.ax.patches) == 8


def test_long_labels_turn_the_bars_horizontal():
    data = pd.DataFrame({"reason": ["Respiratory failure after surgery", "Sepsis", "Sepsis"]})
    figure = hl.bars(data, "reason")
    assert [patch.get_width() for patch in figure.ax.patches] == [2, 1]


def test_stacked_shares_reach_one_hundred_percent():
    figure = hl.bars(admissions(), "diagnosis", by="sex", stacked=True, percent=True)
    tops = {}
    for patch in figure.ax.patches:
        x = round(patch.get_x(), 6)
        tops[x] = max(tops.get(x, 0), patch.get_y() + patch.get_height())
    assert all(top == pytest.approx(1) for top in tops.values())


def outcomes():
    return pd.DataFrame({"unit": ["Medical"] * 5 + ["Surgical"] * 4 + ["Neuro"] * 3,
                         "outcome": ["Home", "Home", "Home", "Ward", "Died", "Home", "Home", "Ward", "Ward",
                                     "Home", "Ward", "Died"]})


def test_stacked_segments_carry_their_values_and_bars_their_totals():
    figure = hl.bars(outcomes(), "unit", by="outcome", stacked=True, sort="given")
    texts = [text.get_text() for text in figure.ax.texts]
    assert texts.count("5") == 1 and texts.count("4") == 1 and texts.count("3") == 2
    inside = [text for text in figure.ax.texts if text.get_gid() == "hairline-segment"]
    assert {text.get_text() for text in inside} >= {"3", "2"}


def test_stacked_shares_label_percentages_and_skip_totals():
    figure = hl.bars(outcomes(), "unit", by="outcome", stacked=True, percent=True, horizontal=True)
    texts = [text.get_text() for text in figure.ax.texts]
    assert "60%" in texts and not any(text.get_gid() == "hairline-total" for text in figure.ax.texts)


def test_stacked_segments_are_separated_by_surface_gaps():
    figure = hl.bars(outcomes(), "unit", by="outcome", stacked=True)
    edges = {mcolors.to_hex(patch.get_edgecolor()) for patch in figure.ax.patches}
    assert edges == {figure.settings.neutral["surface"]}


def test_grouped_bars_name_both_columns_in_the_default_title():
    data = pd.DataFrame({"unit": ["A", "A", "B"], "sex": ["Female", "Male", "Female"]})
    assert hl.bars(data, "unit", by="sex").title == "Count by unit and sex"


def procedures():
    """Four groups of very different size over six years, the first and last incomplete."""
    rows = []
    for group, scale in (("Large", 300), ("Small", 10)):
        for year, count in zip(range(2021, 2027), (2, 12, 12, 12, 12, 10), strict=True):
            rows.append({"group": group, "year": str(year), "cases": count * scale})
    return pd.DataFrame(rows)


def test_facets_get_their_own_value_axis_and_a_total_in_the_header():
    figure = hl.bars(procedures(), "year", "cases", facet="group", sort="given", size="double")
    figure.figure.canvas.draw()
    assert len(figure.axes) == 2
    tops = [ax.get_ylim()[1] for ax in figure.axes]
    assert tops[0] > 10 * tops[1]
    headers = {header.name: dict(header.stats) for header in figure.headers.values()}
    assert headers == {"Large": {"Total": "18,000"}, "Small": {"Total": "600"}}


def test_shared_scales_give_facets_one_value_axis():
    figure = hl.bars(procedures(), "year", "cases", facet="group", scales="shared", sort="given", size="double")
    figure.figure.canvas.draw()
    assert figure.axes[0].get_ylim() == figure.axes[1].get_ylim()


def test_incomplete_periods_are_drawn_lighter_and_named_in_the_caption():
    hl.use(locale="de")
    figure = hl.bars(procedures(), "year", "cases", facet="group", sort="given",
                     partial={"2021": "2 Monate", "2026": "10 Monate"}, caption="Synthetische Daten.")
    alphas = [patch.get_alpha() for patch in figure.axes[0].patches]
    assert alphas[0] == pytest.approx(0.45) and alphas[-1] == pytest.approx(0.45) and alphas[1] is None
    assert figure.caption == "Synthetische Daten. Unvollständig, heller: 2021 (2 Monate), 2026 (10 Monate)."


def test_partial_must_name_a_category():
    with pytest.raises(ValueError, match="partial names '2030'"):
        hl.bars(procedures(), "year", "cases", partial={"2030": "1 month"})


def test_top_folds_the_rest_into_other_per_panel():
    data = pd.DataFrame({"place": list("ABCDEFG") * 2, "group": ["x"] * 7 + ["y"] * 7,
                         "n": [9, 8, 7, 1, 1, 1, 1, 1, 1, 1, 1, 5, 6, 7]})
    figure = hl.bars(data, "place", "n", facet="group", top=3, horizontal=False)
    assert figure.category_axes[(0, "x")] == ["A", "B", "C", "Other"]
    assert [patch.get_height() for patch in figure.axes[0].patches] == [9, 8, 7, 4]
    assert figure.category_axes[(1, "x")][-1] == "Other"


def test_show_n_writes_the_n_after_the_label_and_colours_key_on_the_bare_group():
    hl.use(locale="de")
    data = pd.DataFrame({"unit": ["A"] * 1200 + ["B"] * 3})
    figure = hl.bars(data, "unit", show_n=True, horizontal=True)
    assert figure.category_axes[(0, "y")] == ["B (n = 3)", "A (n = 1 200)"]


def test_normalize_draws_shares_and_keeps_the_n():
    data = pd.DataFrame({"unit": ["A", "A", "A", "B"], "pattern": ["bolus", "bolus", "infusion", "bolus"]})
    figure = hl.bars(data, "unit", by="pattern", stacked=True, normalize=True, horizontal=True)
    widths = [round(patch.get_width(), 4) for patch in figure.ax.patches]
    assert sorted(widths) == [0.0, 0.3333, 0.6667, 1.0]
    assert figure.category_axes[(0, "y")] == ["B (n = 1)", "A (n = 3)"]
    assert (0, "x") in figure.percent_axes


def test_color_by_colours_groups_by_a_coarser_column_and_lists_it_in_the_legend():
    data = pd.DataFrame({"row": ["GA child", "GA adult", "RA child", "RA adult"],
                         "procedure": ["GA", "GA", "RA", "RA"], "n": [3, 5, 2, 4], "year": ["2025"] * 4})
    figure = hl.bars(data, "year", "n", by="row", color_by="procedure")
    figure.figure.canvas.draw()
    colours = [mcolors.to_hex(patch.get_facecolor()) for patch in figure.ax.patches]
    assert colours[0] == colours[1] != colours[2] == colours[3]
    assert figure.layout_report()["legend_labels"] == ["GA", "RA"]


def test_color_by_needs_one_value_per_group():
    data = pd.DataFrame({"row": ["a", "a"], "procedure": ["GA", "RA"], "year": ["1", "1"]})
    with pytest.raises(ValueError, match="gives 'a' more than one value"):
        hl.bars(data, "year", by="row", color_by="procedure")


def side_by_side_shares():
    items = ["Item A long name"] + [f"Item {letter}" for letter in "BCDEFGH"]
    shares = [0.37, 0.39, 0.25, 0.31, 0.33, 0.36, 0.2, 0.4, 0.4, 0.13, 0.44, 0.43, 0.36, 0.38, 0.25, 0.3, 0.51, 0.19,
              0.39, 0.39, 0.22, 0.25, 0.17, 0.57]
    units = ["Unit North", "Unit South", "Unit East"] * len(items)
    return pd.DataFrame({"item": [item for item in items for _ in range(3)], "unit": units, "share": shares})


@pytest.mark.parametrize("facet", [None, "half"])
def test_values_beside_horizontal_bars_side_by_side_stand_apart(facet):
    hl.use(brand=False)
    data = side_by_side_shares().assign(half=["First"] * 12 + ["Second"] * 12)
    figure = hl.bars(data, "item", "share", by="unit", percent=True, horizontal=True, facet=facet)
    assert figure.min_plot > 0
    assert [finding for finding in hl.check_layout(figure) if finding["rule"] == "text_overlap"] == []


def test_one_bar_per_row_keeps_its_height():
    hl.use(brand=False)
    data = side_by_side_shares().query("unit == 'Unit North'")
    assert hl.bars(data, "item", "share", percent=True, horizontal=True).min_plot in (None, 0.0)
