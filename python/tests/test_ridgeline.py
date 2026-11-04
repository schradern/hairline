import numpy as np
import pandas as pd
import pytest

import hairline as hl


def stays():
    generator = np.random.default_rng(6)
    units = ["Surgical", "Medical", "Neuro", "Cardiac"]
    return pd.DataFrame({"unit": np.repeat(units, 50),
                         "length_of_stay": np.concatenate([generator.gamma(2 + index, 2, 50) for index in range(4)])})


def ridges(figure):
    return [patch for patch in figure.ax.patches if patch.get_gid() == "hairline-ridge"]


def test_one_ridge_per_group_first_group_on_top():
    figure = hl.ridgeline(stays(), "unit", "length_of_stay")
    figure.figure.canvas.draw()
    assert [label.get_text() for label in figure.ax.get_yticklabels()] == ["Cardiac", "Neuro", "Medical", "Surgical"]
    bases = [min(point[1] for point in patch.get_xy()) for patch in ridges(figure)]
    assert len(bases) == 4 and bases == sorted(bases, reverse=True)
    assert figure.title == "Length of stay by unit"


def test_ridges_overlap_the_row_above():
    figure = hl.ridgeline(stays(), "unit", "length_of_stay")
    tops = [max(point[1] for point in patch.get_xy()) - min(point[1] for point in patch.get_xy())
            for patch in ridges(figure)]
    assert max(tops) == pytest.approx(1 + 0.6, abs=1e-6)


def test_medians_are_marked():
    figure = hl.ridgeline(stays(), "unit", "length_of_stay")
    marks = [line for line in figure.ax.lines if line.get_gid() == "hairline-median"]
    assert len(marks) == 4
    surgical = stays().query("unit == 'Surgical'")["length_of_stay"].median()
    assert marks[0].get_xdata()[0] == pytest.approx(surgical)


def test_a_group_with_one_value_draws_no_ridge():
    data = pd.DataFrame({"unit": ["A"] * 5 + ["B"], "days": [1, 2, 3, 4, 5, 3]})
    assert len(ridges(hl.ridgeline(data, "unit", "days"))) == 1


def test_ridgeline_shows_n_and_leaves_small_groups_out():
    import pandas as pd
    hl.use(brand=False)
    data = pd.DataFrame({"group": ["a"] * 30 + ["b"] * 2, "value": list(range(30)) + [1, 2]})
    figure = hl.ridgeline(data, "group", "value", show_n=True, min_n=5)
    assert figure.category_axes[(0, "y")] == ["a (n = 30)"]
    assert figure.caption == "Not shown (under 5): b."


def test_ridgeline_clip_keeps_the_ridge_within_the_limit():
    import pandas as pd
    hl.use(brand=False)
    data = pd.DataFrame({"group": ["a"] * 31, "value": list(range(30)) + [3000]})
    figure = hl.ridgeline(data, "group", "value", clip=(None, 100))
    figure.figure.canvas.draw()
    assert figure.ax.get_xlim()[1] < 100
    assert figure.caption == "1 value above 100 not drawn; the statistics use every value."
