"""over_time(): one measure over calendar time by group, as small multiples with a trailing mean."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from hairline.charts.timeseries import timeseries
from hairline.numbers import format_number, is_whole
from hairline.study.columns import is_missing, is_text, numbers
from hairline.study.compare import present_rows, require_values
from hairline.study.describe import counted_rows, group_role, subsets
from hairline.study.result import Result
from hairline.study.summaries import digits_for, left_out_text, listed, mean_text, summary_numbers, summary_text

if TYPE_CHECKING:
    from hairline.study.model import Study


def dated_rows(study: Study, date: str, value: str) -> pd.DataFrame:
    """Rows with the date and the value present; ISO date text becomes dates, anything else is refused."""
    if date not in study.data.columns:
        raise ValueError(f"hairline: over_time: date column '{date}' is not in the data; columns: "
                         f"{', '.join(map(str, study.data.columns))}")
    data = present_rows(study, value)
    data = data[~is_missing(data[date])]
    if is_text(data[date]):
        parsed = pd.to_datetime(data[date], format="ISO8601", errors="coerce")
        if parsed.isna().any():
            bad = data[date][parsed.isna()].iloc[0]
            raise ValueError(f"hairline: over_time: '{date}' has {bad!r}, which is not an ISO date (2025-01-31)")
        data = data.assign(**{date: parsed})
    return data.assign(**{value: data[value].astype(float)})


def over_time(study: Study, date: str, value: str, window: int = 7, size: str = "double") -> Result:
    """Per group the raw values and a trailing mean over `window` observations; the table gives n, mean and
    median (IQR) over the whole period."""
    study.require([study.group, value], "over_time")
    if study.types.get(value) != "numeric":
        raise ValueError(f"hairline: over_time: '{value}' is not numeric")
    data, label = dated_rows(study, date, value), study.label_unit(value)
    values_all = numbers(data[value])
    digits, whole = digits_for(values_all), is_whole(values_all)
    sizes = {name: len(rows) for name, rows in (subsets(study)[:-1] if study.group else subsets(study))}
    key = study.group_key
    found = {name: summary_numbers(numbers(data[data[key] == name][value]), ("mean_sd", "median_iqr"),
                                   size - int((data[key] == name).sum()))
             for name, size in sizes.items()}
    names = [name for name in sizes if found[name]["n"]]
    require_values(names, value, "over_time")
    rows = [[name, format_number(found[name]["n"], 0), summary_text(found[name], "mean_sd", digits, whole),
             summary_text(found[name], "median_iqr", digits, whole)] for name in names]
    figure = timeseries(data.sort_values(date), x=date, y=value, by=key if study.group else None, order=names,
                        window=window, title=f"{study.label(value)} over time", size=size)
    if study.measure(value):
        figure.y_title(study.measure(value))
    means = [mean_text(found[name]["mean"], digits, whole) for name in names]
    parts = listed([f"{name} {mean}" for name, mean in zip(names, means, strict=True)])
    counted = counted_rows(study, {"variable": value, **group_role(study), "date": date})
    text = f"{label}, mean over the period: {parts}." + left_out_text(counted, "rows")
    return Result(figure, pd.DataFrame(rows, columns=["Group", "n", "mean (SD)", "median (IQR)"]),
                  dict(zip(names, means, strict=True)), text, {"rows": counted, "groups": found})
