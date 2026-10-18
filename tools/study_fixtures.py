"""Study endpoint cases for the shared fixtures: data, checks, tables, values and texts that R must reproduce."""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from hairline.study import study


def cohort_data() -> dict[str, list]:
    """Two arms, messy on purpose: a spelling variant, a missing age, a repeated id, numbers stored as text."""
    generator = np.random.default_rng(11)
    count = 40
    sex = [str(value) for value in generator.choice(["Female", "Male"], count)]
    sex[3] = "female "
    age = [float(value) for value in np.round(generator.normal(64, 10, count))]
    return {"id": list(range(1, count)) + [1], "arm": ["Standard care"] * 20 + ["Early mobilisation"] * 20,
            "sex": sex, "age": age[:5] + [None] + age[6:],
            "sofa": [float(value) for value in np.round(generator.gamma(3, 2, count), 1)],
            "score": [str(value) for value in generator.integers(0, 9, count)],
            "months": [float(value) for value in np.round(generator.exponential(12, count), 1)],
            "died": [int(value) for value in generator.integers(0, 2, count)]}


def three_arm_data() -> dict[str, list]:
    generator = np.random.default_rng(12)
    return {"arm": ["A"] * 12 + ["B"] * 12 + ["C"] * 12,
            "lactate": [float(value) for value in np.round(np.concatenate([generator.normal(mean, 0.8, 12)
                                                                           for mean in (2.0, 2.4, 3.1)]), 1)]}


def daily_data() -> dict[str, list]:
    generator = np.random.default_rng(14)
    dates = pd.date_range("2025-01-01", periods=45).strftime("%Y-%m-%d").tolist()
    return {"date": dates * 2, "unit": ["North"] * 45 + ["South"] * 45,
            "occupied": [int(value) for value in generator.integers(4, 14, 90)]}


def frame(data: dict[str, list]) -> pd.DataFrame:
    return pd.DataFrame({name: [np.nan if value is None else value for value in values]
                         for name, values in data.items()})


def result_case(result) -> dict:
    return {"columns": list(result.table.columns), "rows": result.table.values.tolist(), "values": result.values,
            "text": result.text}


def study_cases() -> dict:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        data = cohort_data()
        cohort = study(frame(data), group="arm", time="months", event="died", id="id",
                       variables=["age", "sex", "sofa", "score"], units={"age": "years", "months": "months"})
        three = study(frame(three_arm_data()), group="arm", variables=["lactate"], units={"lactate": "mmol/l"})
        daily = study(frame(daily_data()), group="unit", variables=["occupied"], units={"occupied": "beds"})
        broken = cohort_data()
        broken["died"] = [2] + broken["died"][1:]
        failing = study(frame(broken), group="arm", time="months", event="died", variables=["age"])
    effects = pd.DataFrame({"study": ["age", "sofa"], "estimate": [1.2, 1.8], "low": [1.0, 1.2], "high": [1.5, 2.6]})
    return {"cohort": data, "three": three_arm_data(), "broken_event": broken["died"],
            "checks": [vars(finding) | {"rows": list(finding.rows)} for finding in cohort.checks],
            "broken_checks": [vars(finding) | {"rows": list(finding.rows)} for finding in failing.checks],
            "describe": result_case(cohort.describe(stats=("median_iqr", "mean_sd", "range", "n_missing"))),
            "compare_numeric": result_case(cohort.compare("sofa")),
            "compare_categorical": result_case(cohort.compare("sex")),
            "compare_three": result_case(three.compare("lactate")),
            "distribution": result_case(cohort.distribution("age", stats=("median_iqr", "mean_sd"))),
            "survival": result_case(cohort.survival()),
            "effects_table": effects.to_dict(orient="list"),
            "effects": result_case(cohort.effects(effects, measure="OR")),
            "daily": daily_data(), "over_time": result_case(daily.over_time("date", "occupied"))}


def spread_cases(style: dict, measure) -> dict:
    """Spread rows: whole counts with reference ticks, and shares on a percent axis from zero."""
    from hairline.charts.spread import spread_spec
    from hairline.charts.spread_geometry import spread_drawing
    from hairline.layout.geometry import Box
    generator = np.random.default_rng(13)
    counts = {"group": ["A"] * 30 + ["B"] * 30 + ["C"] * 30,
              "beds": [int(value) for value in np.concatenate([generator.poisson(mean, 30) for mean in (12, 9, 7)])]}
    shares = {"group": counts["group"],
              "share": [round(float(value), 3) for value in generator.beta(6, 2, 90)]}
    box = Box(20, 60, 440, 200)
    cases = []
    for data, value, options in ((counts, "beds", {"marks": {"A": 16, "B": 12}, "mark_label": "Beds"}),
                                 (shares, "share", {"percent": True, "zero": True, "axis_title": "Share",
                                                    "stats": ["median", "iqr", "n"]})):
        spec = spread_spec(pd.DataFrame(data), "group", value, **options)
        cases.append({"data": data, "value": value, "options": options, "spec": spec,
                      "shapes": spread_drawing(spec, box, measure, style)})
    return {"box": [box.x, box.y, box.width, box.height], "style": style, "cases": cases}
