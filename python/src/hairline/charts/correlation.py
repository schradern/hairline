"""Correlation heatmap: lower triangle, diverging ramp, values in the cells, colour key in the
legend row."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from hairline.charts.common import check_columns, humanise
from hairline.charts.correlation_geometry import correlation_drawing
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.numbers import format_number
from hairline.palettes import default_ramp, ramp
from hairline.settings import current_settings
from hairline.stats.tests import ranks
from hairline.tokens import load_tokens


def ramp_color(value: float) -> str:
    """Colour of a correlation on the diverging ramp: -1 at the low pole, 0 at the grey midpoint, 1 at the high pole."""
    colors = ramp(default_ramp("diverging"))
    return colors[round((value + 1) / 2 * (len(colors) - 1))]


def check_varies(rows: pd.DataFrame, columns: Sequence[str]) -> None:
    """Every column needs two different values in the complete rows; a constant one has no correlation."""
    if len(rows) < 2:
        raise ValueError(f"hairline: correlation needs at least 2 rows with every column present; got {len(rows)}")
    for column in columns:
        if rows[column].nunique() < 2:
            raise ValueError(f"hairline: correlation: '{column}' has the same value in every complete row, so its "
                             f"correlations are undefined; leave it out")


def correlation_spec(data: pd.DataFrame, columns: Sequence[str] | None, method: str) -> dict:
    if method not in ("pearson", "spearman"):
        raise ValueError(f"hairline: correlation: method {method!r} must be 'pearson' or 'spearman'")
    columns = list(columns) if columns else [column for column in data.columns
                                             if pd.api.types.is_numeric_dtype(data[column])]
    check_columns(data, columns)
    if len(columns) < 2:
        raise ValueError("hairline: correlation needs at least two numeric columns; got "
                         f"{', '.join(map(str, columns)) or 'none'}")
    rows = data[columns].dropna()
    check_varies(rows, columns)
    values = rows.to_numpy(dtype=float)
    if method == "spearman":
        values = np.column_stack([ranks(values[:, index]) for index in range(values.shape[1])])
    matrix = np.corrcoef(values, rowvar=False)
    locale = current_settings().locale
    return {"names": [humanise(column) for column in columns], "matrix": matrix.tolist(),
            "texts": [[format_number(value, 2, locale) for value in row] for row in matrix],
            "colors": [[ramp_color(value) for value in row] for row in matrix]}


def correlation(data: pd.DataFrame, columns: Sequence[str] | None = None, *, method: str = "pearson",
                title: str | None = None, subtitle: str | None = None, caption: str | None = None,
                size: str = "onehalf") -> HairlineFigure:
    """Correlations between numeric columns (all of them by default); rows with gaps are left out."""
    spec = correlation_spec(data, columns, method)
    result = figure(title or f"{method.title()} correlations", subtitle=subtitle, caption=caption, size=size)
    result.draw(0, lambda box, measure, style: correlation_drawing(spec, box, measure, style))
    locale = current_settings().locale
    result.legend([("square", ramp_color(value), format_number(value, 0 if value == int(value) else 1, locale))
                   for value in load_tokens()["correlation"]["key"]])
    return fit_height(result)
