import pandas as pd
import pytest
from matplotlib.patches import Polygon
from test_donut import STYLE, fake_measure

import hairline as hl
from hairline.charts.swatches_geometry import swatches_drawing
from hairline.layout.geometry import Box
from hairline.palettes import swatch_rows
from hairline.tokens import load_tokens

KINDS = ["categorical", "purpose", "sequential", "diverging"]


@pytest.fixture(autouse=True)
def plain_settings():
    hl.use(brand=False)
    yield
    hl.use(brand=False)


def test_purpose_sets_are_palettes_by_name():
    assert hl.palette("pair") == ["#2474cf", "#ef675a"]
    assert hl.palette("pair-violet") == ["#5152c1", "#ef852e"]
    assert hl.palette("ink", n=3) == ["#1b1e22", "#4a5057", "#767c84"]
    assert hl.palette("judgement") == ["#009775", "#e8a628", "#b93780"]


def test_a_purpose_set_can_be_the_active_palette():
    hl.use(palette="pair")
    data = pd.DataFrame({"arm": ["Control", "Mobilisation", "Control"]})
    assert hl.current_settings().palette == ("#2474cf", "#ef675a")
    hl.bars(data, "arm", by="arm")
    with pytest.raises(ValueError, match="palette 'pair' has 2 slots but 3 categories"):
        hl.palette(n=3)


def test_a_ramp_is_not_a_palette():
    with pytest.raises(ValueError, match=r"'blues' is a ramp, not a palette; use ramp\('blues'\)"):
        hl.palette("blues")


def test_unknown_names_list_palettes_and_purpose_sets():
    with pytest.raises(ValueError, match="available palettes: daylight, bloom, citrus, lagoon, calm, deep, pair, "
                                         "pair-teal, pair-violet, ink, judgement"):
        hl.palette("sunset")


def test_the_catalogue_lists_every_colour_set_with_its_use():
    table = hl.palettes()
    assert list(table.columns) == ["name", "kind", "slots", "active", "use", "colors"]
    assert list(table["kind"].unique()) == KINDS
    assert len(table) == 18
    daylight = table[table["name"] == "daylight"].iloc[0]
    assert daylight["active"] and daylight["slots"] == 8 and daylight["use"] == "bright and balanced; the default"
    assert daylight["colors"].split() == hl.palette("daylight")
    assert table[table["name"] == "blue-coral"].iloc[0]["slots"] == 13


def test_the_catalogue_filters_by_kind():
    assert list(hl.palettes("purpose")["name"]) == ["pair", "pair-teal", "pair-violet", "ink", "judgement"]
    with pytest.raises(ValueError, match="unknown kind 'warm'; use one of categorical, purpose, sequential, diverging"):
        hl.palettes("warm")


def test_a_custom_active_palette_leads_the_catalogue():
    hl.use(palette=["#0b3d6e", "#f2545b"])
    first = hl.palettes().iloc[0]
    assert (first["name"], first["kind"], first["active"], first["colors"]) == \
        ("custom", "categorical", True, "#0b3d6e #f2545b")
    assert not hl.palettes()["active"].iloc[1:].any()


def test_swatch_rows_group_the_sets_under_headings():
    rows = swatch_rows(["pair", "daylight", "blues"])
    assert [row["kind"] for row in rows] == ["categorical", "purpose", "sequential"]
    assert rows[0]["colors"] == hl.palette("daylight")
    with pytest.raises(ValueError, match="unknown colour set 'sunset'"):
        swatch_rows(["sunset"])


def test_swatches_draw_one_tagged_square_per_colour():
    rows = swatch_rows(["daylight", "greys"])
    shapes = swatches_drawing({"rows": rows}, Box(20, 60, 440, 300), fake_measure, STYLE)
    squares = [shape for shape in shapes if shape.get("role") == "swatch"]
    assert len(squares) == 8 + 7
    assert squares[0]["tip"] == "daylight 1: #2474cf" and squares[0]["series"] == "daylight"
    assert squares[8]["tip"] == "greys step 1: #eeeeee"
    texts = [shape["text"] for shape in shapes if shape["kind"] == "text"]
    headings = load_tokens()["swatches"]["headings"]
    assert texts[:3] == [headings["categorical"], "daylight", "bright and balanced; the default"]


def test_near_white_swatches_get_an_outline():
    shapes = swatches_drawing({"rows": swatch_rows(["greys"])}, Box(20, 60, 440, 300), fake_measure, STYLE)
    squares = [shape for shape in shapes if shape.get("role") == "swatch"]
    assert squares[0].get("edge") == STYLE["neutral"]["axis"]
    assert "edge" not in squares[-1]


def test_swatches_figure_shows_every_set_by_default():
    figure = hl.swatches()
    assert figure.title == "Colour sets"
    figure.figure.canvas.draw()
    drawn = [artist for artist in figure.figure.findobj(Polygon) if artist.get_gid() != "hairline-frame"]
    assert len(drawn) >= sum(int(slots) for slots in hl.palettes()["slots"])


def test_swatches_too_narrow_is_named():
    with pytest.raises(ValueError, match="swatches: .* too narrow"):
        swatches_drawing({"rows": swatch_rows(["blue-coral"])}, Box(0, 0, 60, 300), fake_measure, STYLE)


def test_a_ramp_becomes_a_matplotlib_colormap():
    colormap = hl.colormap("blues")
    assert colormap.name == "blues"
    assert colormap(0.0)[:3] == pytest.approx(tuple(int(hl.ramp("blues")[0][i:i + 2], 16) / 255 for i in (1, 3, 5)))
    assert hl.colormap("blue-coral", reverse=True)(0.0)[:3] == pytest.approx(hl.colormap("blue-coral")(1.0)[:3])
    with pytest.raises(ValueError, match=r"'daylight' is a palette, not a ramp; use palette\('daylight'\)"):
        hl.colormap("daylight")
