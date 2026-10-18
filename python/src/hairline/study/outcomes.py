"""survival() and effects(): events over follow-up, and estimates from a model or a results table."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from hairline.charts.forest import forest, model_table
from hairline.charts.kaplan_meier import kaplan_meier
from hairline.numbers import format_interval, format_number, format_p
from hairline.stats.survival import km_estimate, km_median
from hairline.stats.tests import logrank
from hairline.study.columns import is_missing, level_text
from hairline.study.compare import GROUP, listed
from hairline.study.describe import OVERALL
from hairline.study.result import Result
from hairline.tokens import load_tokens

if TYPE_CHECKING:
    from hairline.study.model import Study

NOT_REACHED = "not reached"


def follow_up_rows(study: Study) -> pd.DataFrame:
    time, event = study.roles["time"], study.roles["event"]
    data = study.data.assign(**{time: study.data[time].astype(float), event: study.data[event].astype(int)})
    if not study.group:
        return data.assign(**{GROUP: OVERALL})
    data = data[~is_missing(data[study.group])]
    return data.assign(**{GROUP: data[study.group].map(level_text)})


def survival(study: Study, size: str = "double") -> Result:
    if "time" not in study.roles or "event" not in study.roles:
        raise ValueError("hairline: survival needs time and event; set time= and event= in study()")
    time, event = study.roles["time"], study.roles["event"]
    study.require([time, event, study.group], "survival")
    data = follow_up_rows(study)
    names = [name for name in (study.groups or [OVERALL]) if (data[GROUP] == name).any()]
    rows = []
    for name in names:
        subset = data[data[GROUP] == name]
        median = km_median(km_estimate(subset[time], subset[event]))
        rows.append([name, format_number(len(subset), 0), format_number(int(subset[event].sum()), 0),
                     NOT_REACHED if median is None else format_number(median, 1)])
    test = format_p(logrank(data[time], data[event], data[GROUP])["p"]) if len(names) > 1 else None
    values = {**{row[0]: row[3] for row in rows}, **({"p": test} if test else {})}
    figure = kaplan_meier(data, time, event, by=GROUP if study.group else None, order=names,
                          title=f"Survival by {str(study.group).replace('_', ' ')}" if study.group else "Survival",
                          x_title=study.label(time), size=size)
    medians = listed([f"{row[0]} {row[3]}" for row in rows]) if study.group else rows[0][3]
    text = f"Median {study.label(time).lower()}: {medians}" + (f" (log-rank {test})." if test else ".")
    return Result(figure, pd.DataFrame(rows, columns=["Group", "n", "Events", "Median"]), values, text)


def effect_rows(model_or_table, options: dict) -> pd.DataFrame:
    """Term, estimate, low and high from a fitted model or a table with those columns."""
    if hasattr(model_or_table, "params") and hasattr(model_or_table, "conf_int"):
        return model_table(model_or_table, options.get("exponentiate", False))
    names = [options.get(key, key) for key in ("study", "estimate", "low", "high")]
    missing = [name for name in names if name not in model_or_table.columns]
    if missing:
        raise ValueError(f"hairline: effects: missing columns {', '.join(missing)}; columns: "
                         f"{', '.join(map(str, model_or_table.columns))}")
    return model_or_table[names].set_axis(["term", "estimate", "low", "high"], axis=1)


def effects(study: Study, model_or_table, measure: str | None = None, size: str = "double", **options) -> Result:
    """Estimates with 95 % intervals per term; term names that are study columns take their labels."""
    rows = effect_rows(model_or_table, options).reset_index(drop=True)
    digits, prefix = options.get("digits", 2), f"{measure} " if measure else ""
    terms = [study.label(term) if term in study.data.columns else str(term) for term in rows["term"]]
    texts = [prefix + format_interval(row.estimate, row.low, row.high, digits) for row in rows.itertuples()]
    table = pd.DataFrame({"Term": terms, "Estimate [95 % CI]": texts})
    shown = rows.assign(term=terms)
    passed = {key: value for key, value in options.items() if key not in ("study", "estimate", "low", "high",
                                                                           "exponentiate")}
    ratio_measure = measure in load_tokens()["study"]["ratio_measures"]
    passed.setdefault("ratio", bool(options.get("exponentiate")) or ratio_measure)
    figure = forest(shown, "term", "estimate", "low", "high", size=size, **passed)
    text = "; ".join(f"{term} {value}" for term, value in zip(terms, texts, strict=True)) + "."
    return Result(figure, table, dict(zip(terms, texts, strict=True)), text)
