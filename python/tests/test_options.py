"""Options every chart shares: one helper each, the same name and the same behaviour on every chart that has them."""

import numpy as np
import pandas as pd
import pytest

import hairline as hl
from hairline.charts.options import references, sorted_groups
from hairline.charts.spread import spread_spec
from hairline.interactive import figure_targets
from hairline.marks import context_color


@pytest.fixture(autouse=True)
def plain():
    hl.use(brand=False)


def patients() -> pd.DataFrame:
    rng = np.random.default_rng(4)
    return pd.DataFrame({"group": np.repeat(["Low", "Mid", "High"], 30), "site": np.tile(["North", "South"], 45),
                         "sofa": rng.uniform(1, 14, 90), "lactate": rng.uniform(0.5, 6, 90)})


def texts(figure: hl.HairlineFigure) -> list[str]:
    figure.figure.canvas.draw()
    return [artist.get_text() for artist in figure.figure.findobj(lambda artist: hasattr(artist, "get_text"))]


def test_references_take_a_value_pairs_or_a_mapping():
    assert references(0.9, "bars") == [(0.9, None)]
    assert references((0.9, "Target"), "bars") == [(0.9, "Target")]
    assert references([1, (2, "b")], "bars") == [(1.0, None), (2.0, "b")]
    assert references({"Target": 2}, "bars") == [(2.0, "Target")]
    with pytest.raises(ValueError, match="reference 'x' must be a number"):
        references("x", "bars")


def test_groups_sort_by_median_mean_or_n_and_keep_ties_in_order():
    groups = [("a", np.array([1, 2])), ("b", np.array([5, 6, 7])), ("c", np.array([5, 6, 7]))]
    assert [name for name, _ in sorted_groups(groups, "median", "x")] == ["b", "c", "a"]
    assert [name for name, _ in sorted_groups(groups, "n", "x")] == ["b", "c", "a"]
    assert [name for name, _ in sorted_groups(groups, None, "x")] == ["a", "b", "c"]
    with pytest.raises(ValueError, match="sort 'size' must be one of"):
        sorted_groups(groups, "size", "x")


def test_every_chart_with_a_legend_takes_a_key_title():
    data = patients()
    for figure in (hl.scatter(data, "sofa", "lactate", by="group", key_title="Risk"),
                   hl.bars(data, "site", by="group", key_title="Risk")):
        figure.figure.canvas.draw()
        assert figure.layout_report()["legend_labels"][0] == "Risk"


def test_highlight_greys_the_other_groups_and_names_unknown_ones():
    data = patients()
    figure = hl.scatter(data, "sofa", "lactate", by="group", highlight="High")
    colours = {entry["name"]: entry["color"] for entry in figure_targets(figure)["series"]}
    assert colours["Low"] == colours["Mid"] != colours["High"]
    grey = context_color(hl.current_settings())
    rows = spread_spec(data, "group", "lactate", highlight="High")["rows"]
    assert {row["name"]: row["color"] for row in rows} == {"Low": grey, "Mid": grey, "High": hl.palette()[2]}
    with pytest.raises(ValueError, match="highlight names 'Top', which is not a group"):
        hl.raincloud(data, "group", "lactate", highlight="Top")


def test_min_n_leaves_out_small_groups_and_names_them():
    data = pd.concat([patients(), pd.DataFrame({"group": ["Rare"], "site": ["North"], "sofa": [3.0],
                                                "lactate": [2.0]})])
    for figure in (hl.bars(data, "group", min_n=5), hl.scatter(data, "sofa", "lactate", by="group", min_n=5)):
        assert "Not shown (under 5): Rare." in figure.caption


def test_reference_lines_reach_the_drawn_charts():
    data = patients()
    spread = texts(hl.spread(data, "group", "lactate", reference={"Upper normal": 2}))
    assert "Upper normal" in spread
    rates = pd.DataFrame({"unit": ["A", "B"], "rate": [0.1, 0.2], "low": [0.05, 0.1], "high": [0.2, 0.3]})
    assert "Target" in texts(hl.dotplot(rates, "unit", "rate", "low", "high", reference=(0.15, "Target")))


def test_facets_draw_panels_or_blocks():
    data = patients()
    assert len(hl.scatter(data, "sofa", "lactate", facet="site").axes) == 2
    assert len(hl.raincloud(data, "group", "lactate", facet="site").axes) == 2
    shown = texts(hl.spread(data, "group", "lactate", facet="site"))
    assert {"North", "South"} <= set(shown) and "Low" in shown and "North · Low" not in shown
    with pytest.raises(ValueError, match="facet and section both draw blocks"):
        hl.spread(data, "group", "lactate", facet="site", section="site")


def test_dotplot_takes_order_min_n_and_facets():
    rates = pd.DataFrame({"unit": ["A", "B", "C"] * 2, "year": ["2024"] * 3 + ["2025"] * 3,
                          "rate": [0.1, 0.2, 0.3] * 2, "n": [50, 40, 3] * 2})
    figure = hl.dotplot(rates, "unit", "rate", n="n", min_n=10, facet="year", order=["B", "A"])
    shown = texts(figure)
    assert "Not shown (under 10): C, C." in figure.caption and {"2024", "2025"} <= set(shown)
    with pytest.raises(ValueError, match="min_n needs n="):
        hl.dotplot(rates, "unit", "rate", min_n=10)


def test_ridgeline_facets_draw_panels_with_their_n():
    data = patients()
    figure = hl.ridgeline(data, "group", "lactate", facet="site", show_n=True)
    assert len(figure.axes) == 2
    assert [header.stats for header in figure.headers.values()] == [(("n", "45"),), (("n", "45"),)]


def test_show_n_false_leaves_n_out_of_dotplot_and_likert():
    rates = pd.DataFrame({"unit": ["A", "B"], "rate": [0.1, 0.2], "n": [50, 40]})
    assert "A (n = 50)" in texts(hl.dotplot(rates, "unit", "rate", n="n"))
    shown = texts(hl.dotplot(rates, "unit", "rate", n="n", show_n=False, min_n=45))
    assert "A" in shown and "A (n = 50)" not in shown and "B" not in shown
    ratings = pd.DataFrame({"item": np.repeat(["Clear", "Kind"], 20), "rating": np.tile([1, 2, 3, 4, 5], 8)})
    labels = [[text.strip() for text in texts(hl.likert(ratings, "item", "rating", show_n=shown))]
              for shown in (True, False)]
    assert "n" in labels[0] and "n" not in labels[1]


def test_ridgeline_keeps_room_for_reference_labels():
    data = patients()
    plain = hl.ridgeline(data, "group", "lactate", reference=2).ax.get_ylim()[1]
    labelled = hl.ridgeline(data, "group", "lactate", reference={"Upper normal": 2}).ax.get_ylim()[1]
    assert labelled > plain
