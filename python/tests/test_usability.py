import numpy as np
import pandas as pd
import pytest

import hairline as hl


def discharges():
    return pd.DataFrame({"route": ["Home"] * 5 + ["Rehabilitation"] * 3 + ["Care home"] * 2,
                         "detail": ["Alone"] * 3 + ["With support"] * 2 + ["Inpatient"] * 3 + ["Care home"] * 2})


def stays():
    generator = np.random.default_rng(2)
    return pd.DataFrame({"unit": ["Surgical"] * 30 + ["Medical"] * 30 + ["Neuro"] * 30,
                         "length_of_stay": np.concatenate([generator.gamma(2, 2, 30), generator.gamma(3, 2, 30),
                                                           generator.gamma(4, 2.5, 30)]).round(1)})


def trial():
    generator = np.random.default_rng(4)
    return pd.DataFrame({"arm": ["A"] * 40 + ["B"] * 40, "months": generator.exponential(12, 80).round(1),
                         "died": (generator.uniform(size=80) < 0.7).astype(int)})


def test_titles_come_from_the_columns():
    assert hl.raincloud(stays(), "unit", "length_of_stay").title == "Length of stay by unit"
    assert hl.donut(discharges(), "route").title == "Count by route"
    assert hl.partition(discharges(), ["route", "detail"]).title == "Count by route and detail"
    assert hl.kaplan_meier(trial(), "months", "died", by="arm").title == "Survival by arm"


def test_raw_rows_are_counted():
    rings = hl.donut(discharges(), "route").drawings[0]
    figure = hl.donut(discharges(), "route")
    figure.figure.canvas.draw()
    assert rings is not None
    texts = [shape["text"] for shape in figure.shapes if shape["kind"] == "text"]
    assert "50%" in texts and "10" in texts


def test_kaplan_meier_adds_the_log_rank_test():
    stats = dict(hl.kaplan_meier(trial(), "months", "died", by="arm").headers[0].stats)
    assert stats["Log-rank"].startswith("p ")


def test_raincloud_computes_its_comparisons():
    figure = hl.raincloud(stays(), "unit", "length_of_stay", comparisons="all")
    labels = [text.get_text() for text in figure.ax.texts]
    assert len(labels) == 3 and all(label.startswith("p ") for label in labels)
    figure = hl.raincloud(stays(), "unit", "length_of_stay", comparisons=[("Surgical", "Neuro")])
    assert [text.get_text() for text in figure.ax.texts][0].startswith("p ")


class FittedModel:
    """The parts of a statsmodels results object the forest plot reads."""
    params = pd.Series({"Intercept": -1.2, "age": 0.03, "sepsis": 0.6})
    bse = pd.Series({"Intercept": 0.4, "age": 0.01, "sepsis": 0.2})

    def conf_int(self):
        return pd.DataFrame({0: self.params - 1.96 * self.bse, 1: self.params + 1.96 * self.bse})


def test_forest_reads_a_fitted_model():
    figure = hl.forest(FittedModel(), exponentiate=True)
    figure.figure.canvas.draw()
    texts = [shape["text"] for shape in figure.shapes if shape["kind"] == "text"]
    assert "age" in texts and "sepsis" in texts and "Intercept" not in texts
    assert any(text.startswith("1.82 [") for text in texts)
    assert figure.title == "Effects by term"


def test_forest_needs_columns_for_a_table():
    with pytest.raises(ValueError, match="needs the study, estimate, low and high columns"):
        hl.forest(pd.DataFrame({"a": [1]}))
