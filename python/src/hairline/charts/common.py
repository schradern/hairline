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
