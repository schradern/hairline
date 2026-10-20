"""survival() and effects(): events over follow-up, and estimates from a model or a results table."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pandas as pd

from hairline.charts.forest import forest, model_table, ratio_model
from hairline.charts.kaplan_meier import estimates_from, kaplan_meier
from hairline.numbers import format_interval, format_number, format_p
from hairline.stats.survival import km_median, median_digits
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


def survival_rows(estimates: list) -> list[list[str]]:
    rows, digits = [], median_digits([table for _, table, _ in estimates])
    for name, table, total in estimates:
        median = km_median(table)
        rows.append([name or OVERALL, format_number(total, 0), format_number(int(table["events"].sum()), 0),
                     NOT_REACHED if median is None else format_number(median, digits)])
    return rows


def survival(study: Study, fit=None, size: str = "double") -> Result:
    """Kaplan–Meier by group from the study's time and event, or from a fit already made (a lifelines
    KaplanMeierFitter or a mapping of group to one); the log-rank test needs the study's own columns."""
    roles = study.roles
    if fit is None and ("time" not in roles or "event" not in roles):
        raise ValueError("hairline: survival needs time and event; set time= and event= in study(), or pass fit=")
    has_data = "time" in roles and "event" in roles
    if has_data:
        study.require([roles["time"], roles["event"], study.group], "survival")
    data = follow_up_rows(study) if has_data else None
    if fit is None:
        names = [name for name in (study.groups or [OVERALL]) if (data[GROUP] == name).any()]
        estimates = estimates_from(data, roles["time"], roles["event"], GROUP, names)
    else:
        estimates = estimates_from(fit, None, None, None, None)
        if study.groups and {name for name, _, _ in estimates} <= set(study.groups):
            estimates.sort(key=lambda item: study.groups.index(item[0]))
        names = [name or OVERALL for name, _, _ in estimates]
    rows = survival_rows(estimates)
    grouped = len(estimates) > 1
    shown = data[data[GROUP].isin(names)] if fit is None and has_data else data
    test = logrank_text(shown, roles) if grouped and has_data and study.group else None
    values = {**{row[0]: row[3] for row in rows}, **({"p": test} if test else {})}
    time_label = study.label_unit(roles["time"]) if "time" in roles else "Time"
    figure = kaplan_meier(fit if fit is not None else data, roles.get("time"), roles.get("event"),
                          by=GROUP if fit is None and study.group else None, order=names if fit is None else None,
                          title=f"Survival by {str(study.group).replace('_', ' ')}" if grouped and study.group
                          else "Survival", x_title=time_label, size=size, test=False,
                          stats=[("Log-rank", test)] if test else ())
    return Result(figure, pd.DataFrame(rows, columns=["Group", "n", "Events", "Median"]), values,
                  survival_text(study, rows, grouped, test))


def logrank_text(data: pd.DataFrame, roles: dict) -> str | None:
    """The log-rank p over the groups shown; none when no event makes the test undefined."""
    p = logrank(data[roles["time"]], data[roles["event"]], data[GROUP])["p"]
    return None if math.isnan(p) else format_p(p)


def survival_text(study: Study, rows: list, grouped: bool, test: str | None) -> str:
    time = study.roles.get("time")
    measured = study.label(time).lower() if time else "survival time"
    unit = f" ({study.measure(time)})" if time and study.measure(time) else ""
    medians = listed([f"{row[0]} {row[3]}" for row in rows]) if grouped else rows[0][3]
    return f"Median {measured}{unit}: {medians}" + (f" (log-rank {test})." if test else ".")


def effect_rows(model_or_table, columns: tuple[str, str, str, str], exponentiate: bool | None) -> pd.DataFrame:
    """Term, estimate, low and high from a fitted model or a table with those columns."""
    if hasattr(model_or_table, "params") and hasattr(model_or_table, "conf_int"):
        return model_table(model_or_table, ratio_model(model_or_table) if exponentiate is None else exponentiate)
    missing = [name for name in columns if name not in model_or_table.columns]
    if missing:
        raise ValueError(f"hairline: effects: missing columns {', '.join(missing)}; columns: "
                         f"{', '.join(map(str, model_or_table.columns))}")
    return model_or_table[list(columns)].set_axis(["term", "estimate", "low", "high"], axis=1)


def effects(study: Study, model_or_table, measure: str | None = None, size: str = "double", *,
            study_column: str = "study", estimate: str = "estimate", low: str = "low", high: str = "high",
            exponentiate: bool | None = None, digits: int = 2, **options) -> Result:
    """Estimates with 95 % intervals per term from a fitted model or a table; term names that are study columns
    take their labels. `options` go to forest()."""
    rows = effect_rows(model_or_table, (study_column, estimate, low, high), exponentiate).reset_index(drop=True)
    prefix = f"{measure} " if measure else ""
    terms = [study.label(term) if term in study.data.columns else str(term) for term in rows["term"]]
    texts = [prefix + format_interval(row.estimate, row.low, row.high, digits) for row in rows.itertuples()]
    table = pd.DataFrame({"Term": terms, "Estimate [95 % CI]": texts})
    modelled = hasattr(model_or_table, "params")
    exponentiated = (ratio_model(model_or_table) if exponentiate is None else exponentiate) if modelled \
        else bool(exponentiate)
    ratio = exponentiated or measure in load_tokens()["study"]["ratio_measures"]
    figure = forest(rows.assign(term=terms), "term", "estimate", "low", "high", ratio=ratio, size=size,
                    digits=digits, **options)
    text = "; ".join(f"{term} {value}" for term, value in zip(terms, texts, strict=True)) + "."
    return Result(figure, table, dict(zip(terms, texts, strict=True)), text)
