"""Input checks and data preparation shared by the chart functions."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd


def check_columns(data: pd.DataFrame, columns: Sequence[str | None]) -> None:
    for column in columns:
        if column is not None and column not in data.columns:
            known = ", ".join(map(str, data.columns))
            raise ValueError(f"hairline: column {column!r} is not in the data; columns: {known}")


def check_labels(data: pd.DataFrame, columns: Sequence[str | None], chart: str) -> None:
    """Every row names its group; a missing label would become a group called 'nan' or lose its rows."""
    for column in columns:
        if column is None:
            continue
        missing = np.flatnonzero(pd.isna(data[column]).to_numpy())
        if len(missing):
            raise ValueError(f"hairline: {chart}: '{column}' is missing in row {missing[0] + 1}; every row needs a "
                             f"name there: fill it (e.g. 'Unknown') or drop the row")


def check_numeric(data: pd.DataFrame, columns: Sequence[str], chart: str) -> None:
    """Measurements are numbers; text or dates in a value column get a message rather than a failed calculation."""
    for column in columns:
        values = data[column]
        if not pd.api.types.is_numeric_dtype(values) or pd.api.types.is_bool_dtype(values):
            raise ValueError(f"hairline: {chart}: '{column}' holds {values.dtype} values; it needs numbers")


def check_present(data: pd.DataFrame, column: str, chart: str) -> None:
    """Something to draw: at least one row with a value."""
    if not data[column].notna().any():
        raise ValueError(f"hairline: {chart}: no values to draw; '{column}' is empty or missing in every row")


def group_names(values: pd.Series) -> list[str]:
    """Groups as text: a categorical's present categories in their order, otherwise in order of first appearance."""
    if isinstance(values.dtype, pd.CategoricalDtype):
        present = {str(value) for value in values.dropna()}
        return [str(name) for name in values.cat.categories if str(name) in present]
    return [str(name) for name in dict.fromkeys(values.dropna())]


def ordered_names(values: pd.Series, order: Sequence | None, chart: str, column: str,
                  complete: bool = False) -> list[str]:
    """The groups in `order`, which may only name groups in the data; with `complete`, the groups it leaves out
    follow in data order (flows need every node), otherwise they are left out."""
    names = group_names(values)
    if order is None:
        return names
    wanted = [str(name) for name in order]
    unknown = [name for name in wanted if name not in names]
    if unknown:
        raise ValueError(f"hairline: {chart}: order names {unknown[0]!r}, which is not a group in '{column}'; "
                         f"groups: {', '.join(names)}")
    return wanted + [name for name in names if name not in wanted] if complete else wanted


def flow_rows(data: pd.DataFrame, source: str, target: str, value: str, chart: str,
              order: Sequence | None) -> tuple[pd.DataFrame, list[str]]:
    """Rows with a value, and the node names (those in `order` first, the rest in data order). Missing names,
    negative values and flows from a node to itself are refused: a ring or a baseline cannot draw a self-flow."""
    check_columns(data, [source, target, value])
    check_labels(data, [source, target], chart)
    rows = data[data[value].notna()]
    negative = rows[rows[value] < 0]
    if len(negative):
        first = negative.iloc[0]
        raise ValueError(f"hairline: {chart}: {first[source]} – {first[target]} has a negative value "
                         f"({first[value]}); flows need values of zero or more")
    selves = rows[(rows[source].astype(str) == rows[target].astype(str)) & (rows[value] > 0)]
    if len(selves):
        raise ValueError(f"hairline: {chart}: {selves.iloc[0][source]} → {selves.iloc[0][source]} flows to itself; "
                         f"a {chart} diagram draws flows between different groups, so leave those rows out")
    if not (rows[value] > 0).any():
        raise ValueError(f"hairline: {chart}: no flows above zero to draw in '{value}'")
    pairs = pd.Series([name for pair in zip(data[source], data[target], strict=True) for name in pair])
    return rows, ordered_names(pairs, order, chart, f"{source}' or '{target}", complete=True)


def fold_other(labels: Sequence[str], values: Sequence[float], keep: int = 7,
               other: str = "Other") -> tuple[list[str], list[float]]:
    """More than `keep` entries: the `keep - 1` largest stay in given order, the rest sum into `other`. An entry
    already named `other` always joins the rest, so the chart never shows two of them."""
    labels, values = list(labels), list(values)
    if len(labels) <= keep:
        return labels, values
    candidates = [index for index in range(len(values)) if labels[index] != other]
    ranked = sorted(candidates, key=lambda index: (-values[index], index))[:keep - 1]
    kept = sorted(ranked)
    rest = sum(value for index, value in enumerate(values) if index not in kept)
    return [labels[index] for index in kept] + [other], [values[index] for index in kept] + [rest]


COUNT = "Count"


def humanise(name: str) -> str:
    """A column name as words: 'length_of_stay' -> 'Length of stay'."""
    words = str(name).replace("_", " ").replace(".", " ").strip()
    return words[:1].upper() + words[1:]


def joined(names: Sequence[str]) -> str:
    names = [str(name).replace("_", " ") for name in names]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


COUNT_NAMES = (COUNT, "Rows", "Row count")


def count_column(data: pd.DataFrame) -> str:
    """A name for the row counts that no data column has: Count, else Rows, else Row count, else numbered."""
    taken = {str(column) for column in data.columns}
    candidates = [*COUNT_NAMES, *(f"{COUNT} {index}" for index in range(2, len(taken) + 3))]
    return next(name for name in candidates if name not in taken)


def with_counts(data: pd.DataFrame, value: str | None) -> tuple[pd.DataFrame, str]:
    """Raw rows count one each when no value column is given; the count never overwrites a data column."""
    if value is not None:
        return data, value
    name = count_column(data)
    return data.assign(**{name: 1}), name
