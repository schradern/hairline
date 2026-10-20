"""A study: a dataset described once (which column plays which role), checked when it is created."""

from __future__ import annotations

import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import pandas as pd

from hairline.charts.common import humanise
from hairline.study.checks import Finding, missing_values, numbers_as_text, spellings
from hairline.study.columns import infer_type, levels
from hairline.study.result import Result
from hairline.study.rules import event_findings, group_findings, id_findings, time_findings
from hairline.tokens import load_tokens

ROLES = ("group", "time", "event", "id")


@dataclass
class Study:
    data: pd.DataFrame
    roles: dict[str, str]
    variables: list[str]
    labels: dict[str, str]
    types: dict[str, str]
    groups: list[str]
    unit: str
    checks: list[Finding] = field(default_factory=list)
    units: dict[str, str] = field(default_factory=dict)

    @property
    def group(self) -> str | None:
        return self.roles.get("group")

    def label(self, column: str) -> str:
        return self.labels.get(column, humanise(column))

    def measure(self, column: str) -> str | None:
        """The column's unit, e.g. "years" or "mmol/l"; none when the label already says it ("Months")."""
        unit = self.units.get(column)
        return None if unit and unit.lower() == self.label(column).lower() else unit

    def label_unit(self, column: str) -> str:
        """'Age (years)', or the bare label without a unit."""
        unit = self.measure(column)
        return f"{self.label(column)} ({unit})" if unit else self.label(column)

    def kind(self, column: str, endpoint: str) -> str:
        """The variable's type; a role column (follow-up time) is typed from its values."""
        if column not in self.data.columns:
            raise ValueError(f"hairline: {endpoint}: '{column}' is not a column of the study; columns: "
                             f"{', '.join(map(str, self.data.columns))}")
        return self.types.get(column) or infer_type(self.data[column])

    def require(self, columns: Sequence[str | None], endpoint: str) -> None:
        """Refuse an endpoint while its columns have errors; name each one."""
        errors = [finding for finding in self.checks if finding.level == "error" and finding.column in columns]
        if errors:
            raise ValueError(f"hairline: {endpoint}: fix these first:\n" + "\n".join(f"- {item}" for item in errors))

    def __str__(self) -> str:
        roles = ", ".join(f"{role} = {column}" for role, column in self.roles.items())
        lines = [f"Study of {len(self.data)} {self.unit}: {roles or 'no roles'}; {len(self.variables)} variables"]
        return "\n".join(lines + [f"- {finding}" for finding in self.checks] or ["- no problems found"])

    def describe(self, stats: Sequence[str] = ("median_iqr",), size: str = "double") -> Result:
        from hairline.study.describe import describe
        return describe(self, stats, size)

    def distribution(self, variable: str, stats: Sequence[str] = ("median_iqr",), size: str = "double") -> Result:
        from hairline.study.compare import distribution
        return distribution(self, variable, stats, size)

    def compare(self, variable: str, size: str = "double") -> Result:
        from hairline.study.compare import compare
        return compare(self, variable, size)

    def survival(self, fit=None, size: str = "double") -> Result:
        from hairline.study.outcomes import survival
        return survival(self, fit, size)

    def over_time(self, date: str, value: str, window: int = 7, size: str = "double") -> Result:
        from hairline.study.trends import over_time
        return over_time(self, date, value, window, size)

    def effects(self, model_or_table, measure: str | None = None, size: str = "double", **options) -> Result:
        """Effects from a model or a table; options: study_column, estimate, low, high, exponentiate, digits."""
        from hairline.study.outcomes import effects
        return effects(self, model_or_table, measure, size, **options)


KINDS = ("numeric", "categorical")


def check_kinds(kinds: Mapping[str, str]) -> None:
    """Variables are numeric or categorical; dates are followed over time, not summarised in a table."""
    for name, kind in kinds.items():
        if kind == "date":
            raise ValueError(f"hairline: study: '{name}' holds dates, which tables do not summarise; leave it out of "
                             f"variables and follow a measure over it with over_time()")
        if kind not in KINDS:
            raise ValueError(f"hairline: study: type {kind!r} for '{name}' is not one of {', '.join(KINDS)}")


def unit_findings(roles: dict[str, str], variables: list[str], types: dict[str, str],
                  units: Mapping[str, str]) -> list[Finding]:
    """Numeric variables (and follow-up time) need a unit, so mixed tables and panels say what they measure."""
    measured = [*([roles["time"]] if "time" in roles else []), *(name for name in variables
                                                              if types.get(name) == "numeric")]
    missing = [str(name) for name in measured if not units.get(name)]
    if not missing:
        return []
    return [Finding("warning", ", ".join(missing), "numeric columns without a unit", (),
                    "give each a unit, for example years or mmol/l, so tables and panels name it")]


def run_checks(data: pd.DataFrame, roles: dict[str, str], variables: list[str], groups: list[str]) -> list[Finding]:
    limit, columns = load_tokens()["study"]["example_rows"], set(data.columns)
    named = [*roles.items(), *(("variable", name) for name in variables)]
    choices = f"use one of: {', '.join(map(str, data.columns))}"
    findings = [Finding("error", name, f"not in the data (role: {role})", (), choices)
                for role, name in named if name not in columns]
    checks = {"time": time_findings, "event": event_findings}
    for role in ("time", "event"):
        if roles.get(role) in columns:
            findings += checks[role](data, roles[role], limit)
    if roles.get("group") in columns:
        findings += group_findings(data, roles["group"], groups, limit)
    if roles.get("id") in columns:
        findings += id_findings(data, roles["id"], limit)
    for name in (name for name in variables if name in columns):
        findings += missing_values(data, name, limit) + spellings(data, name, limit) + numbers_as_text(data, name)
    return findings


def study(data: pd.DataFrame, group: str | None = None, time: str | None = None, event: str | None = None,
          id: str | None = None, variables: Sequence[str] | None = None, *, labels: Mapping[str, str] | None = None,
          types: Mapping[str, str] | None = None, order: Sequence[str] | None = None,
          unit: str | None = None, units: Mapping[str, str] | None = None) -> Study:
    """Describe a dataset once: the comparison `group`, follow-up `time` and `event`, the `id`, the `variables`
    to characterise (default: every other column) and their `units` ({"age": "years"}). Checks run now; print
    the study to read them."""
    if not len(data):
        raise ValueError("hairline: study: the data has no rows")
    roles = {role: column for role, column in zip(ROLES, (group, time, event, id), strict=True) if column is not None}
    used = set(roles.values())
    names = list(variables) if variables is not None else [column for column in data.columns if column not in used
                                                           and infer_type(data[column]) != "date"]
    kinds = {name: (types or {}).get(name) or infer_type(data[name]) for name in names if name in data.columns}
    check_kinds(kinds)
    groups = list(order) if order else (levels(data[group], ordered=False) if group in data.columns else [])
    checks = run_checks(data, roles, names, groups) + unit_findings(roles, names, kinds, units or {})
    result = Study(data, roles, names, dict(labels or {}), kinds, groups,
                   unit or load_tokens()["study"]["unit"], checks, dict(units or {}))
    if checks:
        errors = sum(finding.level == "error" for finding in checks)
        warnings.warn(f"hairline: study: {errors} errors, {len(checks) - errors} warnings; print the study to read "
                      "them", stacklevel=2)
    return result
