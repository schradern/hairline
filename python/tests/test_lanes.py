"""Lanes, levels and swimlanes over the time of day, checked against values worked out by hand."""

import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import pytest

import hairline as hl
from hairline.charts.time_of_day import calendar, first_free, hour_window, short_label, step_index
from hairline.interactive import figure_targets
from hairline.stats.density import level_quantiles


def stays() -> pd.DataFrame:
    """Two weekdays: theatre 1 busy 08:00-08:30 on the first only, recovery 1 from 08:30 to 09:00 on both."""
    return pd.DataFrame({
        "place": ["Theatre 1", "Recovery 1", "Recovery 1"], "section": ["Theatre", "Recovery", "Recovery"],
        "start": pd.to_datetime(["2026-03-02 08:00", "2026-03-02 08:30", "2026-03-03 08:30"]),
        "end": pd.to_datetime(["2026-03-02 08:30", "2026-03-02 09:00", "2026-03-03 09:00"])})


def test_quantiles_on_levels_match_r_type_1():
    assert level_quantiles([1, 2, 3, 4], [0.5, 0.9, 0.25]) == [2.0, 4.0, 1.0]
    assert level_quantiles([0, 0, 0, 0, 0, 0, 0, 0, 0, 3], [0.9]) == [0.0]


def test_first_free_gives_each_task_the_first_person_free():
    assert first_free([0, 1, 2, 5], [2, 3, 4, 6]) == [1, 2, 1, 1]


def test_float_noise_in_a_data_limit_adds_no_hour_to_the_window():
    assert hour_window([6.999999999999998], [18.75], 1) == (6, 20)
    assert hour_window([7.25], [18.000000000000004], 1) == (6, 19)


def test_calendar_keeps_weekdays_and_names_them_with_their_n():
    days, label = calendar(pd.Timestamp("2026-03-02"), pd.Timestamp("2026-03-08"), "weekdays", "lanes")
    assert len(days) == 5 and label == "Weekdays, 5 days"
    with pytest.raises(ValueError, match="must be 'weekdays', 'weekends' or a list of dates"):
        calendar(pd.Timestamp("2026-03-02"), pd.Timestamp("2026-03-08"), "mondays", "lanes")


def test_rows_in_a_block_read_by_number_and_cells_bin_as_the_key():
    assert short_label("Theatre 2", "Theatre") == "2" and short_label("Bay A", "Theatre") == "Bay A"
    assert [step_index(value, [0.25, 0.5, 0.75, 1]) for value in (0.1, 0.25, 0.26, 0.5, 1)] == [0, 0, 1, 1, 3]


def test_lanes_colour_each_cell_by_the_share_of_days_occupied():
    hl.use(brand=False)
    figure = hl.lanes(stays(), "place", "start", "end", group="section")
    tips = [mark["text"] for mark in figure.hover_marks]
    assert tips == ["Theatre 1, 08:00–08:15: 50%", "Theatre 1, 08:15–08:30: 50%",
                    "Recovery 1, 08:30–08:45: 100%", "Recovery 1, 08:45–09:00: 100%"]
    assert figure.subtitle == "All days, 2 days"
    cells = figure.ax.collections[0].get_facecolors()
    assert mcolors.to_hex(cells[0]) != mcolors.to_hex(cells[2])
    figure.figure.canvas.draw()
    assert figure.ax.get_xlim() == (7.0, 10.0)
    assert figure.layout_report()["legend_labels"] == ["Share of days", "25%", "50%", "75%", "100%"]


def test_lanes_flows_connect_rows_per_bin_by_moves_per_day():
    hl.use(brand=False)
    moves = pd.DataFrame({"from": ["Theatre 1"], "to": ["Recovery 1"],
                          "time": pd.to_datetime(["2026-03-02 08:30"])})
    figure = hl.lanes(stays(), "place", "start", "end", group="section", flows=moves)
    lines = figure.ax.collections[1]
    assert np.allclose(lines.get_segments()[0], [[8.625, 1.0], [8.625, 0.0]])
    assert figure.legend_items[-1].label == "Move"
    with pytest.raises(ValueError, match="flows name 'Ward'"):
        hl.lanes(stays(), "place", "start", "end", flows=moves.assign(to="Ward"))


def test_lanes_html_carries_a_tooltip_per_cell():
    hl.use(brand=False)
    targets = figure_targets(hl.lanes(stays(), "place", "start", "end", group="section"))
    assert sum(len(series["tips"]) for series in targets["series"]) == 4


def staff() -> pd.DataFrame:
    """Day one two people 08:00-09:00, day two one person."""
    return pd.DataFrame({"role": ["Doctors"] * 3,
                         "start": pd.to_datetime(["2026-03-02 08:00", "2026-03-02 08:00", "2026-03-03 08:00"]),
                         "end": pd.to_datetime(["2026-03-02 09:00", "2026-03-02 09:00", "2026-03-03 09:00"])})


def test_levels_draw_the_decision_and_the_typical_day_on_whole_levels():
    hl.use(brand=False)
    figure = hl.levels(staff(), "start", end="end", by="role")
    decision = next(line for line in figure.ax.lines if line.get_drawstyle() == "steps-post"
                    and line.get_linestyle() == "-")
    assert set(decision.get_ydata()) == {2.0}
    assert dict(figure.headers[0].stats) == {"Up to": "2", "Typical": "1"}
    assert "Quantiles on the data's own levels." in figure.caption
    figure.figure.canvas.draw()
    assert [label.get_text() for label in figure.ax.get_yticklabels()] == ["0", "1", "2"]


def test_levels_from_counts_sampled_at_times():
    hl.use(brand=False, locale="de")
    samples = pd.DataFrame({"time": pd.to_datetime(["2026-03-02 08:05", "2026-03-03 08:05", "2026-03-04 08:05"]),
                            "nurses": [3, 1, 1]})
    figure = hl.levels(samples, "time", "nurses", quantile=0.5)
    assert dict(figure.headers[0].stats) == {"Bis": "1", "Typisch": "1"}
    assert figure.legend_items[0].label == "Ausreichend an 50 % der Tage"


def test_levels_and_lanes_share_one_time_axis_in_a_composed_figure():
    hl.use(brand=False)
    figure = hl.figure("Cause above effect", panels=2, heights=(3, 2), sharex=True, size="double", height_mm=120)
    hl.lanes(stays(), "place", "start", "end", group="section", into=figure, panel=0)
    hl.levels(staff(), "start", end="end", into=figure, panel=1)
    figure.figure.canvas.draw()
    assert figure.axes[0].get_xlim() == figure.axes[1].get_xlim()
    assert figure.category_axes[(0, "y")] == ["1", "1"]
    assert not figure.axes[0].xaxis.get_tick_params()["labelbottom"]


def test_swimlanes_place_each_interval_in_its_row_and_assign_people():
    hl.use(brand=False)
    tasks = pd.DataFrame({"task": ["P1", "P2", "P3"], "start": [8.0, 8.5, 9.0], "end": [9.0, 9.5, 10.0],
                          "role": ["Doctor"] * 3})
    figure = hl.swimlanes(tasks, None, "start", "end", label="task", group="role", assign="first_free")
    assert figure.category_axes[(0, "y")] == ["2", "1"]
    assert [mark["text"] for mark in figure.hover_marks] == ["P1 · Doctor 1: 08:00–09:00",
                                                            "P2 · Doctor 2: 08:30–09:30",
                                                            "P3 · Doctor 1: 09:00–10:00"]
    figure.figure.canvas.draw()
    assert all(artist.get_visible() for _, artist, _, _ in figure.inside_labels)


def test_swimlanes_hide_labels_too_wide_for_their_bar():
    hl.use(brand=False)
    tasks = pd.DataFrame({"place": ["A", "A"], "who": ["A very long patient name", "P2"], "start": [8.0, 9.0],
                          "end": [8.1, 12.0]})
    figure = hl.swimlanes(tasks, "place", "start", "end", label="who", size="single")
    figure.figure.canvas.draw()
    assert [artist.get_visible() for _, artist, _, _ in figure.inside_labels] == [False, True]
