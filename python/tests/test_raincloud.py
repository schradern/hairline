import numpy as np
import pandas as pd
import pytest

import hairline as hl
from hairline.charts.raincloud import bracket_levels


def stays():
    generator = np.random.default_rng(5)
    return pd.DataFrame({"unit": ["Surgical"] * 60 + ["Medical"] * 60 + ["Neuro"] * 40,
                         "days": np.round(np.concatenate([generator.gamma(2.2, 2.0, 60), generator.gamma(3.0, 2.2, 60),
                                                          generator.gamma(4.0, 2.5, 40)]), 1)})


def test_brackets_do_not_overlap():
    levels = bracket_levels([(0, 1), (1, 2), (0, 2)])
    assert levels == [0, 1, 2]
    assert bracket_levels([(0, 1), (0, 1)]) == [0, 1]


def test_single_value_group_draws_no_density():
    data = pd.DataFrame({"unit": ["A"] * 5 + ["B"], "days": [1, 2, 3, 4, 5, 3]})
    figure = hl.raincloud(data, "unit", "days", title="Length of stay")
    assert len([patch for patch in figure.ax.patches if patch.get_gid() == "hairline-density"]) == 1


def test_n_labels_under_groups():
    figure = hl.raincloud(stays(), "unit", "days", title="Length of stay")
    figure.figure.canvas.draw()
    report = figure.layout_report()
    assert figure.table_spec["rows"][0][2] == [(0.0, "n = 60"), (1.0, "n = 60"), (2.0, "n = 40")]
    assert [label.get_text() for label in figure.ax.get_xticklabels()] == ["Surgical", "Medical", "Neuro"]
    assert len(report["table_value_xs"]) == 3


def test_comparison_names_must_be_groups():
    with pytest.raises(ValueError, match="comparison group 'ICU' is not one of: Surgical, Medical, Neuro"):
        hl.raincloud(stays(), "unit", "days", title="T", comparisons=[("Surgical", "ICU", "p = 0.01")])
