import numpy as np
import pandas as pd
import pytest

import hairline as hl
from hairline.ticks import nice_breaks


def trial():
    generator = np.random.default_rng(3)
    rows = []
    for arm, scale in (("Standard care", 10.0), ("Early mobilisation", 16.0)):
        times = np.round(generator.exponential(scale, 80), 1)
        events = (generator.uniform(size=80) < 0.75).astype(int)
        rows += [{"arm": arm, "months": time, "died": event} for time, event in zip(times, events, strict=True)]
    return pd.DataFrame(rows)


def drawn(figure):
    figure.figure.canvas.draw()
    return figure.layout_report()


def test_curves_start_at_one_and_step_down():
    figure = hl.kaplan_meier(trial(), "months", "died", by="arm", title="Survival")
    drawn(figure)
    curves = [line for line in figure.ax.lines if line.get_label() in ("Standard care", "Early mobilisation")]
    assert len(curves) == 2
    for curve in curves:
        ys = curve.get_ydata()
        assert ys[0] == 1 and all(np.diff(ys) <= 1e-12)
        assert curve.get_drawstyle() == "steps-post"


def test_at_risk_values_align_with_ticks():
    data = trial()
    figure = hl.kaplan_meier(data, "months", "died", by="arm", title="Survival")
    report = drawn(figure)
    ticks = figure.ax.get_xticks()
    box = report["plot_boxes"][0]
    low, high = figure.ax.get_xlim()
    expected = [box[0] + (tick - low) / (high - low) * box[2] for tick in ticks]
    assert report["table_value_xs"][:len(ticks)] == pytest.approx(expected, abs=0.5)
    assert list(ticks) == pytest.approx(nice_breaks(0, data["months"].max()))


def test_median_not_reached_is_named():
    data = pd.DataFrame({"months": [1, 2, 3, 4, 5], "died": [1, 0, 0, 0, 0]})
    figure = hl.kaplan_meier(data, "months", "died", title="Survival")
    assert ("Median", "not reached") in figure.headers[0].stats


def test_user_stats_follow_the_medians():
    figure = hl.kaplan_meier(trial(), "months", "died", by="arm", title="Survival",
                             stats=[("HR", "0.64 [0.45, 0.91]"), ("Log-rank p", "0.012")])
    labels = [label for label, _ in figure.headers[0].stats]
    assert labels == ["Median", "HR", "Log-rank p"]
    assert " vs " in figure.headers[0].stats[0][1]


def test_number_at_risk_heading_and_rows():
    figure = hl.kaplan_meier(trial(), "months", "died", by="arm", title="Survival")
    report = drawn(figure)
    assert len(report["table_baselines"]) == 3
    assert figure.table_spec["heading"] == "Number at risk"


def test_missing_column_is_named():
    with pytest.raises(ValueError, match="column 'days' is not in the data"):
        hl.kaplan_meier(trial(), "days", "died", title="Survival")


def test_at_risk_keys_match_the_legend_lines():
    from hairline.layout.table import label_offset
    figure = hl.kaplan_meier(trial(), "months", "died", by="arm")
    drawn(figure)
    assert figure.table_keys == ["line", "line"]
    spacing, base = hl.load_tokens()["spacing"], figure.settings.base_size
    assert label_offset(figure) == pytest.approx((spacing["legend_swatch_line"] + spacing["legend_swatch_text"]) * base)
