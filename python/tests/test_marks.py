import matplotlib.colors as mcolors
import numpy as np
import pytest

import hairline as hl
from hairline.color.space import hex_to_oklch
from hairline.color.vision import contrast
from hairline.layout.legend import items_from_axes
from hairline.marks import line_style, point_fill, point_step, point_style, series_colors


def test_series_colors_follow_slot_order():
    colors = series_colors(["Home", "Rehab", "Ward"])
    assert colors == {"Home": "#2474cf", "Rehab": "#ef675a", "Ward": "#b93780"}


def test_too_many_categories_message():
    with pytest.raises(ValueError, match="palette 'daylight' has 8 slots but 9 categories were given"):
        series_colors([f"group {index}" for index in range(9)])


def test_light_slot_line_is_heavier():
    settings = hl.use()
    regular, light = line_style("#2474cf", settings), line_style("#e8a628", settings)
    assert regular["linewidth"] == pytest.approx(0.14 * 9)
    assert light["linewidth"] == pytest.approx(1.3 * 0.14 * 9)


def test_dark_colour_keeps_its_point_fill():
    assert point_fill("#2474cf", "#ffffff") == "#2474cf"


def test_light_colour_gets_darker_point_fill_of_the_same_hue():
    fill = point_fill("#e8a628", "#ffffff")
    given, used = hex_to_oklch("#e8a628"), hex_to_oklch(fill)
    assert contrast(fill, "#ffffff") >= 3
    assert given[0] - 0.2 < used[0] < given[0]
    assert used[2] == pytest.approx(given[2], abs=3)


@pytest.mark.parametrize(("count", "radius", "opacity"), [
    (1, 0.2, 0.9), (200, 0.2, 0.9), (201, 0.14, 0.7), (1000, 0.14, 0.7), (5000, 0.1, 0.5), (5001, 0.07, 0.35)])
def test_point_size_and_opacity_follow_the_count(count, radius, opacity):
    assert point_step(count) == (radius, opacity)


def test_point_style_has_no_outline():
    settings = hl.use()
    style = point_style("#e8a628", settings, count=2000)
    assert style["markeredgewidth"] == 0
    assert style["color"] == point_fill("#e8a628", "#ffffff")
    assert style["markersize"] == pytest.approx(2 * 0.1 * 9)
    assert style["alpha"] == pytest.approx(0.5)


def test_series_colors_with_custom_palette_label():
    hl.use(palette=["#112233", "#445566"])
    with pytest.raises(ValueError, match="custom palette has 2 slots but 3 categories"):
        series_colors(["a", "b", "c"])


def test_figure_applies_light_slot_treatment_once():
    figure = hl.figure("T")
    regular = figure.ax.plot([0, 1], [0, 1], color="#2474cf")[0]
    light = figure.ax.plot([0, 1], [1, 0], color="#e8a628")[0]
    points = figure.ax.scatter([0.5], [0.5], color="#e8a628")
    base_width = regular.get_linewidth()
    for _ in range(2):
        figure.figure.canvas.draw()
    assert light.get_linewidth() == pytest.approx(1.3 * base_width)
    assert regular.get_linewidth() == pytest.approx(base_width)
    assert mcolors.to_hex(points.get_facecolor()[0]) == point_fill("#e8a628", "#ffffff")
    assert points.get_linewidths()[0] == 0


def test_dense_points_are_smaller_and_more_transparent():
    figure = hl.figure("T")
    values = np.linspace(0, 1, 2000)
    points = figure.ax.scatter(values, values[::-1])
    figure.figure.canvas.draw()
    assert points.get_sizes()[0] == pytest.approx((2 * 0.1 * 9) ** 2)
    assert points.get_alpha() == pytest.approx(0.5)


def test_explicit_point_size_and_opacity_are_kept():
    figure = hl.figure("T")
    points = figure.ax.scatter([0, 1], [0, 1], s=40, alpha=0.3)
    figure.figure.canvas.draw()
    assert points.get_sizes()[0] == pytest.approx(40)
    assert points.get_alpha() == pytest.approx(0.3)


def test_legend_swatch_shows_the_darker_fill():
    figure = hl.figure("T")
    figure.ax.scatter([0], [0], color="#f2c14e", label="Rehab")
    figure.ax.scatter([1], [1], color="#1f5fa8", label="Home")
    figure.figure.canvas.draw()
    colours = {item.label: item.color for item in items_from_axes(figure.axes)}
    assert colours == {"Rehab": point_fill("#f2c14e", "#ffffff"), "Home": "#1f5fa8"}


def test_context_points_follow_the_count_without_darker_fill():
    figure = hl.figure("T")
    values = np.linspace(0, 1, 300)
    points = figure.ax.scatter(values, values, label="Trauma")
    figure.ax.plot([0, 1], [1, 0], label="Sepsis")
    figure.highlight(series=["Sepsis"])
    figure.figure.canvas.draw()
    assert mcolors.to_hex(points.get_facecolor()[0]) == "#b3b8be"
    assert points.get_sizes()[0] == pytest.approx((2 * 0.14 * 9) ** 2)
