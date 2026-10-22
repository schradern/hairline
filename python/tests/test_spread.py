import json
import logging

import numpy as np
import pandas as pd
import pytest
from matplotlib import font_manager

import hairline as hl
from hairline import host
from hairline.charts.donut_geometry import line_height
from hairline.charts.spread import spread_spec
from hairline.charts.spread_geometry import spread_drawing, spread_layout
from hairline.errors import HairlineLayoutError
from hairline.fonts import installed_families
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens

STYLE = {"base": 9.0, "sizes": {"title": 13.5, "panel": 9.0, "label": 7.2, "caption": 7.2}, "line_gap": 0.25,
         "cap_height": 0.7, "descender": 0.21, "leader_width": 0.54, "data_width": 1.26, "axis_width": 0.585,
         "grid": 0.45, "neutral": {"ink": "#1b1e22", "muted": "#5b6168", "faint": "#6f757d", "axis": "#c4c8cd",
                                   "surface": "#ffffff", "band": "#f2f3f5", "grid": "#eef0f2"}}


def measure(text: str, role: str, weight: int | None = None) -> float:
    return 0.5 * STYLE["sizes"][role] * len(text)


def nights() -> pd.DataFrame:
    """Seven groups of response speeds, as in the demo paper that showed the collapse."""
    generator = np.random.default_rng(3)
    return pd.DataFrame({"Night": np.repeat([f"Night {index}" for index in range(1, 8)], 40),
                         "speed": np.concatenate([generator.normal(3.2 - 0.12 * index, 0.4, 40)
                                                  for index in range(7)])})


def spec(**options) -> dict:
    hl.use(brand=False)
    return spread_spec(nights(), "Night", "speed", axis_title="Response speed (1/s)", **options)


def numbers(shapes: list[dict], name: str) -> list[dict]:
    """The key-number texts of one row: every text of the row after its name, in drawing order."""
    texts = [shape for shape in shapes if shape["kind"] == "text" and "part" not in shape]
    start = next(index for index, shape in enumerate(texts) if shape["text"] == name)
    return texts[start + 1: start + 7]


@pytest.fixture
def narrow_context(tmp_path, monkeypatch):
    """The host context Papers hands a figure in one column of a two-column PDF design."""
    path = tmp_path / "context.json"
    path.write_text(json.dumps({"version": 1, "host": "editor", "output": "pdf", "width_mm": 75}))
    monkeypatch.setenv(host.ENVIRONMENT, str(path))
    yield
    monkeypatch.delenv(host.ENVIRONMENT, raising=False)
    host._state.update(path=None, context=None)


def test_numbers_sit_beside_the_plot_at_a_normal_width():
    rules, data = load_tokens()["spread"], spec()
    layout = spread_layout(data, Box(20, 60, 440, 300), measure, STYLE, rules)
    left, right = layout["plot"]
    assert not layout["under"]
    assert right - left >= rules["min_plot"] * STYLE["base"]
    assert layout["lefts"][0] > right
    shapes = spread_drawing(data, Box(20, 60, 440, 300), measure, STYLE)
    name = next(shape for shape in shapes if shape.get("text") == "Night 1")
    assert {shape["y"] for shape in numbers(shapes, "Night 1")} == {name["y"]}


def test_numbers_move_under_each_row_when_the_plot_would_fall_below_its_minimum():
    rules, data, box = load_tokens()["spread"], spec(), Box(20, 60, 240, 300)
    layout = spread_layout(data, box, measure, STYLE, rules)
    left, right = layout["plot"]
    assert layout["under"] and right == box.x + box.width
    assert layout["lefts"][0] == box.x and left > box.x
    shapes = spread_drawing(data, box, measure, STYLE)
    name = next(shape for shape in shapes if shape.get("text") == "Night 1")
    row = numbers(shapes, "Night 1")
    assert [shape["y"] for shape in row] == pytest.approx([name["y"] + line_height(STYLE, "label")] * len(row))
    assert [shape["text"].strip() for shape in row[::2]] == ["Median", "IQR", "Mean"]
    assert max(shape["x"] + measure(shape["text"], "label") for shape in row) <= box.x + box.width
    following = next(shape for shape in shapes if shape.get("text") == "Night 2")
    assert following["y"] - row[0]["y"] > line_height(STYLE, "label")


def test_ticks_keep_their_order_and_room_at_every_width():
    data = spec()
    for width in (180, 240, 300, 360, 440):
        shapes = spread_drawing(data, Box(20, 60, width, 300), measure, STYLE)
        ticks = [shape for shape in shapes if shape.get("part") == "tick"]
        for this, after in zip(ticks, ticks[1:], strict=False):
            room = (measure(this["text"], "label") + measure(after["text"], "label")) / 2
            assert after["x"] - this["x"] > room


def test_a_figure_too_narrow_for_the_plot_and_numbers_names_the_room_needed():
    with pytest.raises(HairlineLayoutError, match="spread: the figure leaves 120 pt for the rows"):
        spread_drawing(spec(), Box(20, 60, 120, 300), measure, STYLE)


def test_without_numbers_the_plot_reaches_the_right_edge():
    data = spec(stats=[])
    layout = spread_layout(data, Box(20, 60, 200, 300), measure, STYLE, load_tokens()["spread"])
    assert layout == {"plot": (layout["plot"][0], 220), "lefts": [], "under": False}


def test_spread_at_a_two_column_width_keeps_its_plot(narrow_context):
    hl.use(brand=False)
    figure = hl.spread(nights(), "Night", "speed", axis_title="Response speed (1/s)", title="Response speed by night")
    assert figure.figure.get_size_inches()[0] * 25.4 == pytest.approx(75)
    ticks = [shape for shape in figure.shapes if shape.get("part") == "tick"]
    assert [shape["x"] for shape in ticks] == sorted(shape["x"] for shape in ticks)
    box = figure.plot_boxes[0]
    assert ticks[-1]["x"] - ticks[0]["x"] >= load_tokens()["spread"]["min_plot"] * figure.settings.base_size
    assert ticks[-1]["x"] <= box.x + box.width


@pytest.mark.skipif("Helvetica Neue" not in installed_families(), reason="needs Helvetica Neue, which has no semibold")
def test_a_family_without_semibold_draws_its_bold_without_a_fallback_notice(caplog):
    hl.use(brand=False, font="Helvetica Neue")
    font_manager.fontManager._findfont_cached.cache_clear()
    with caplog.at_level(logging.INFO, logger="matplotlib.font_manager"):
        hl.spread(nights(), "Night", "speed", title="Response speed by night")
    assert not [record for record in caplog.records if "Failed to find font weight" in record.getMessage()]
