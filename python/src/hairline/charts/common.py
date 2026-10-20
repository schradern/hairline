"""Input checks and data preparation shared by the chart functions."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd


def check_columns(data: pd.DataFrame, columns: Sequence[str | None]) -> None:
    for column in columns:
        if column is not None and column not in data.columns:
            known = ", ".join(map(str, data.columns))
            raise ValueError(f"hairline: column {column!r} is not in the data; columns: {known}")


def fold_other(labels: Sequence[str], values: Sequence[float], keep: int = 7,
               other: str = "Other") -> tuple[list[str], list[float]]:
    """More than `keep` entries: the `keep - 1` largest stay in given order, the rest sum into `other`."""
    labels, values = list(labels), list(values)
    if len(labels) <= keep:
        return labels, values
    ranked = sorted(range(len(values)), key=lambda index: (-values[index], index))[:keep - 1]
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
