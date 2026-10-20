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
from hairline.study.describe import counted_rows, group_role
from hairline.study.result import Result
from hairline.study.summaries import left_out_text, listed
from hairline.tokens import load_tokens

if TYPE_CHECKING:
    from hairline.study.model import Study

NOT_REACHED = "not reached"


def follow_up_rows(study: Study) -> pd.DataFrame:
    time, event = study.roles["time"], study.roles["event"]
    data = study.data.assign(**{time: study.data[time].astype(float), event: study.data[event].astype(int)})
    if not study.group:
        return data.assign(**{study.group_key: study.overall})
    data = data[~is_missing(data[study.group])]
    return data.assign(**{study.group_key: data[study.group].map(level_text)})


def survival_rows(estimates: list, overall: str) -> tuple[list[list[str]], dict]:
    """Per group n, events and the median (NaN when not reached), and the table rows formatted from them."""
    digits = median_digits([table for _, table, _ in estimates])
    found = {}
    for name, table, total in estimates:
        median = km_median(table)
        found[name or overall] = {"n": int(total), "events": int(table["events"].sum()),
                                  "median": math.nan if median is None else float(median)}
    rows = [[name, format_number(group["n"], 0), format_number(group["events"], 0),
             NOT_REACHED if math.isnan(group["median"]) else format_number(group["median"], digits)]
            for name, group in found.items()]
    return rows, found


def survival_estimates(study: Study, data: pd.DataFrame | None, fit) -> tuple[list, list[str]]:
    """Kaplan–Meier tables per group from the rows, or from a fit in the study's group order; and the group names."""
    if fit is None:
        names = [name for name in (study.groups or [study.overall]) if (data[study.group_key] == name).any()]
        return estimates_from(data, study.roles["time"], study.roles["event"], study.group_key, names), names
    estimates = estimates_from(fit, None, None, None, None)
    if study.groups and {name for name, _, _ in estimates} <= set(study.groups):
        estimates.sort(key=lambda item: study.groups.index(item[0]))
    return estimates, [name or study.overall for name, _, _ in estimates]


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
    estimates, names = survival_estimates(study, data, fit)
    rows, groups = survival_rows(estimates, study.overall)
    grouped = len(estimates) > 1
    shown = data[data[study.group_key].isin(names)] if fit is None and has_data else data
    test = logrank_test(shown, roles, study.group_key) if grouped and has_data and study.group else None
    p = None if test is None or math.isnan(test["p"]) else format_p(test["p"])
    values = {**{row[0]: row[3] for row in rows}, **({"p": p} if p else {})}
    time_label = study.label_unit(roles["time"]) if "time" in roles else "Time"
    by = study.group_key if fit is None and study.group else None
    figure = kaplan_meier(fit if fit is not None else data, roles.get("time"), roles.get("event"),
                          by=by, order=names if fit is None else None,
                          title=f"Survival by {str(study.group).replace('_', ' ')}" if grouped and study.group
                          else "Survival", x_title=time_label, size=size, test=False,
                          stats=[("Log-rank", p)] if p else ())
    # Time and event cannot be missing: the study's checks block survival() then.
    found = {**({"rows": counted_rows(study, group_role(study))} if has_data else {}), "groups": groups,
             **({"test": test} if test else {})}
    text = survival_text(study, rows, grouped, p) + (left_out_text(found["rows"], study.unit) if has_data else "")
    return Result(figure, pd.DataFrame(rows, columns=["Group", "n", "Events", "Median"]), values, text, found)


def logrank_test(data: pd.DataFrame, roles: dict, key: str) -> dict:
    """The log-rank test over the groups shown (in column `key`); p is NaN when no event makes it undefined."""
    found = logrank(data[roles["time"]], data[roles["event"]], data[key])
    return {"method": "Log-rank", "statistic": found["chisq"], "df": int(found["df"]), "p": found["p"]}


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


def model_references(model) -> dict[str, str]:
    """Reference levels of treatment-coded factors, from a formula model's design info (patsy) where it has one:
    the level whose contrast row is all zeros."""
    info = getattr(getattr(getattr(model, "model", None), "data", None), "design_info", None)
    references: dict[str, str] = {}
    for subterms in getattr(info, "term_codings", {}).values():
        for factor, contrast in ((factor, contrast) for subterm in subterms
                                 for factor, contrast in subterm.contrast_matrices.items()):
            categories = info.factor_infos[factor].categories
            zero = [category for category, row in zip(categories, contrast.matrix, strict=True) if not any(row)]
            if len(zero) == 1:
                references[factor.name()] = level_text(zero[0])
    return references


def effects(study: Study, model_or_table, measure: str | None = None, size: str = "double", *,
            study_column: str = "study", estimate: str = "estimate", low: str = "low", high: str = "high",
            exponentiate: bool | None = None, digits: int = 2, **options) -> Result:
    """Estimates with 95 % intervals per term from a fitted model or a table; term names that are study columns
    take their labels. `options` go to forest()."""
    rows = effect_rows(model_or_table, (study_column, estimate, low, high), exponentiate).reset_index(drop=True)
    prefix = f"{measure} " if measure else ""
    terms = [study.label(term) if term in study.data.columns else str(term) for term in rows["term"]]
    estimates = [{"estimate": float(row.estimate), "low": float(row.low), "high": float(row.high)}
                 for row in rows.itertuples()]
    texts = [prefix + format_interval(item["estimate"], item["low"], item["high"], digits) for item in estimates]
    table = pd.DataFrame({"Term": terms, "Estimate [95 % CI]": texts})
    modelled = hasattr(model_or_table, "params")
    exponentiated = (ratio_model(model_or_table) if exponentiate is None else exponentiate) if modelled \
        else bool(exponentiate)
    ratio = exponentiated or measure in load_tokens()["study"]["ratio_measures"]
    figure = forest(rows.assign(term=terms), "term", "estimate", "low", "high", ratio=ratio, size=size,
                    digits=digits, **options)
    text = "; ".join(f"{term} {value}" for term, value in zip(terms, texts, strict=True)) + "."
    found = {"scale": "ratio" if ratio else "difference",
             "reference": model_references(model_or_table) if modelled else {},
             "terms": dict(zip(terms, estimates, strict=True))}
    return Result(figure, table, dict(zip(terms, texts, strict=True)), text, found)
