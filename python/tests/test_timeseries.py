import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import pytest

import hairline as hl


def occupancy() -> pd.DataFrame:
    days = pd.date_range("2025-01-01", periods=60, freq="D")
    rows = []
    for ward, level in (("Unit A", 0.6), ("Unit B", 0.88), ("Unit D", 0.78)):
        rng = np.random.default_rng(len(ward))
        rows += [{"date": day, "share": level + rng.normal(0, 0.05), "ward": ward} for day in days]
    return pd.DataFrame(rows)


def drawn(figure):
    figure.figure.canvas.draw()
    return figure


def data_lines(ax):
    return [line for line in ax.lines if line.get_gid() != "hairline-reference"]


def test_one_panel_per_group_with_two_levels_of_detail():
    hl.use()
    figure = drawn(hl.timeseries(occupancy(), x="date", y="share", by="ward", title="ICU bed occupancy"))
    assert len(figure.axes) == 3 and [header.name for header in figure.headers.values()] == ["Unit A", "Unit B",
                                                                                              "Unit D"]
    raw, mean = data_lines(figure.axes[0])
    assert raw.get_alpha() == pytest.approx(0.3) and raw.get_linewidth() == pytest.approx(0.055 * 9)
    assert mean.get_linewidth() == pytest.approx(0.14 * 9)
    assert mcolors.to_hex(mean.get_color()) == mcolors.to_hex(raw.get_color()) == hl.color("Unit A")
    light_raw, light_mean = data_lines(figure.axes[1])
    assert light_raw.get_linewidth() == pytest.approx(0.055 * 9)
    assert light_mean.get_linewidth() == pytest.approx(1.3 * 0.14 * 9)


def test_trailing_rolling_mean_with_partial_windows():
    hl.use()
    data = pd.DataFrame({"x": range(5), "y": [1.0, 3.0, 5.0, 7.0, 9.0]})
    figure = hl.timeseries(data, x="x", y="y", title="T", window=3)
    _, mean = data_lines(figure.axes[0])
    assert list(mean.get_ydata()) == pytest.approx([1.0, 2.0, 3.0, 5.0, 7.0])


def test_key_numbers_threshold_and_key():
    hl.use()
    figure = hl.timeseries(occupancy(), x="date", y="share", by="ward", title="T", percent=True, threshold=0.9,
                           threshold_label="90 %", stats=("mean", "median", "share_above"),
                           share_label="Days ≥ 90%", key="share_above", key_panels=["Unit B"])
    header = figure.headers[1]
    assert [label for label, _ in header.stats] == ["Mean", "Median", "Days ≥ 90%"]
    assert header.key == "Days ≥ 90%" and figure.headers[0].key is None
    assert all(any(line.get_gid() == "hairline-reference" for line in ax.lines) for ax in figure.axes)


def test_period_mean_bands_and_events_with_legend():
    hl.use()
    figure = hl.timeseries(occupancy(), x="date", y="share", by="ward", title="T", period_mean=True,
                           bands=[{"start": "2025-01-20", "end": "2025-02-10", "label": "Interim, reduced beds"}],
                           events=[{"x": "2025-01-20", "label": "Move out"}], raw_label="Daily value",
                           mean_label="7-day mean")
    drawn(figure)
    assert figure.layout_report()["legend_labels"] == ["Daily value", "7-day mean", "Period mean",
                                                       "Interim, reduced beds"]
    ax = figure.axes[0]
    assert len(ax.patches) == 1 and [text.get_text() for text in ax.texts] == ["Move out"]


def test_date_axes_use_the_shared_month_ticks():
    hl.use()
    days = pd.date_range("2025-01-01", "2026-06-30", freq="D")
    data = pd.DataFrame({"date": days, "share": np.linspace(0.5, 0.9, len(days))})
    figure = drawn(hl.timeseries(data, x="date", y="share", title="T"))
    labels = [label.get_text() for label in figure.axes[0].get_xticklabels() if label.get_text()]
    assert labels == ["2025", "May", "Sep", "2026", "May"]


def test_highlight_greys_the_other_panels():
    hl.use()
    figure = drawn(hl.timeseries(occupancy(), x="date", y="share", by="ward", title="T", highlight=["Unit B"]))
    assert mcolors.to_hex(data_lines(figure.axes[0])[1].get_color()) == "#b3b8be"
    assert mcolors.to_hex(data_lines(figure.axes[1])[1].get_color()) == hl.color("Unit B")


def test_missing_column_is_named():
    with pytest.raises(ValueError, match="column 'occupancy' is not in the data; columns: date, share, ward"):
        hl.timeseries(occupancy(), x="date", y="occupancy", by="ward", title="T")


def test_month_names_follow_the_locale():
    hl.use(locale="de")
    days = pd.date_range("2025-01-01", "2026-06-30", freq="D")
    data = pd.DataFrame({"date": days, "share": np.linspace(0.5, 0.9, len(days))})
    figure = drawn(hl.timeseries(data, x="date", y="share", title="T"))
    labels = [label.get_text() for label in figure.axes[0].get_xticklabels() if label.get_text()]
    assert labels == ["2025", "Mai", "Sep", "2026", "Mai"]


def test_date_axis_spans_exactly_the_data():
    import matplotlib.dates as mdates
    hl.use()
    days = pd.date_range("2025-01-01", "2025-12-31", freq="D")
    figure = drawn(hl.timeseries(pd.DataFrame({"date": days, "share": 0.5}), x="date", y="share", title="T"))
    low, high = figure.axes[0].get_xlim()
    assert (mdates.num2date(low).date().isoformat(), mdates.num2date(high).date().isoformat()) == (
        "2025-01-01", "2025-12-31")


def test_event_labels_sit_at_the_panel_bottom():
    hl.use()
    figure = drawn(hl.timeseries(occupancy(), x="date", y="share", by="ward", title="T",
                                 events=[{"x": "2025-01-20", "label": "Move out"}]))
    note = figure.axes[0].texts[0]
    assert note.get_va() == "bottom" and note.xy[1] == 0
