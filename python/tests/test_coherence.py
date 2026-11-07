"""One design across charts: names in ink, keys from the left, locale interval headings, colours with one meaning."""

import pandas as pd
import pytest

import hairline as hl
from hairline.interactive import figure_targets
from hairline.layout.ticking import names_axis


@pytest.fixture(autouse=True)
def plain():
    hl.use(brand=False)


def tick_colors(figure: hl.HairlineFigure, which: str) -> set[str]:
    figure.figure.canvas.draw()
    axis = figure.axes[0].yaxis if which == "y" else figure.axes[0].xaxis
    return {hl_hex(label.get_color()) for label in axis.get_ticklabels() if label.get_text()}


def hl_hex(color) -> str:
    from matplotlib.colors import to_hex
    return to_hex(color)


def test_names_are_ink_and_numbers_faint():
    neutral = hl.current_settings().neutral
    figure = hl.bars(pd.DataFrame({"unit": ["Medical", "Surgical"], "n": [3, 5]}), "unit", "n", horizontal=True)
    assert tick_colors(figure, "y") == {neutral["ink"]}
    assert tick_colors(figure, "x") == {neutral["faint"]}
    years = hl.bars(pd.DataFrame({"year": ["2024", "2025"], "n": [3, 5]}), "year", "n", horizontal=False)
    assert tick_colors(years, "x") == {neutral["faint"]}
    assert names_axis(["Unit A"]) and not names_axis(["1", "2", "−3"])


def test_a_binned_key_starts_at_the_left_edge():
    figure = hl.likert(pd.DataFrame({"s": ["A"] * 5 + ["B"] * 5, "r": list(range(1, 6)) * 2}), "s", "r",
                       levels=range(1, 6))
    legend = figure_targets(figure)["legend"]
    assert legend[0]["box"][0] == pytest.approx(figure.layout_report()["left"], abs=0.01)


def test_interval_headings_follow_the_locale():
    rates = pd.DataFrame({"unit": ["A", "B"], "mortality": [0.1, 0.2], "low": [0.05, 0.1], "high": [0.2, 0.3]})
    figure = hl.dotplot(rates, "unit", "mortality", "low", "high", percent=True, digits=0)
    texts = figure_texts(figure)
    assert "Mortality (%) [95% CI]" in texts and "10 [5; 20]" in texts
    hl.use(brand=False, locale="de")
    assert "Mortality (%) [95 %-KI]" in figure_texts(hl.dotplot(rates, "unit", "mortality", "low", "high",
                                                                 percent=True, digits=0))


def figure_texts(figure: hl.HairlineFigure) -> list[str]:
    figure.figure.canvas.draw()
    return [text.get_text() for text in figure.figure.findobj(lambda artist: hasattr(artist, "get_text"))]


def test_a_ramp_name_colours_ordered_groups_light_to_dark():
    with hl.entities.chart(["Low", "Medium", "High"], "blues") as palette:
        colours = [palette[name] for name in ("Low", "Medium", "High")]
    assert colours == hl.ramp("blues", 5)[2:]
    with pytest.raises(ValueError, match="unknown ramp"), hl.entities.chart(["Low"], "nope"):
        pass


def test_levels_by_role_shade_in_greys_and_arcs_name_their_key():
    staff = pd.DataFrame({"start": ["2026-01-05 08:00", "2026-01-05 09:00"], "end": ["2026-01-05 12:00",
                                                                                   "2026-01-05 15:00"],
                          "role": ["Doctors", "Nurses"]})
    figure = hl.levels(staff, "start", end="end", by="role")
    colours = {entry["color"] for entry in figure_targets(figure)["series"]}
    assert colours and not colours & set(hl.palette()[:2])
    moves = pd.DataFrame({"origin": ["ICU", "Ward"], "destination": ["Ward", "Home"]})
    assert "Count" in figure_texts(hl.arcs(moves, "origin", "destination"))
    assert "Moves" in figure_texts(hl.arcs(moves, "origin", "destination", key_title="Moves"))
