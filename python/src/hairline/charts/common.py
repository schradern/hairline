"""Input checks and data preparation shared by the chart functions."""

from __future__ import annotations

import math
import numbers
from collections.abc import Mapping, Sequence

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
        check_distinct_text(data[column], column, chart)


def check_distinct_text(values: pd.Series, column: str, chart: str) -> None:
    """Groups are named by their text, so two values that read the same (1 and "1") would merge into one."""
    seen: dict[str, object] = {}
    for value in dict.fromkeys(values):
        other = seen.setdefault(str(value), value)
        if other is not value and other != value:
            raise ValueError(f"hairline: {chart}: '{column}' holds {other!r} and {value!r}, which read the same; "
                             f"give the column one type")


def check_numeric(data: pd.DataFrame, columns: Sequence[str], chart: str) -> None:
    """Measurements are numbers; text or dates in a value column get a message rather than a failed calculation."""
    for column in columns:
        values = data[column]
        if not pd.api.types.is_numeric_dtype(values) or pd.api.types.is_bool_dtype(values):
            raise ValueError(f"hairline: {chart}: '{column}' holds {values.dtype} values; it needs numbers")
        check_finite(data, column, chart)


def check_finite(data: pd.DataFrame, column: str, chart: str) -> None:
    """An infinite value has no place on an axis, in a sum or a share; missing values are left out elsewhere."""
    if not pd.api.types.is_numeric_dtype(data[column]) or pd.api.types.is_bool_dtype(data[column]):
        return
    infinite = np.flatnonzero(np.isinf(data[column].to_numpy(dtype=float, na_value=np.nan)))
    if len(infinite):
        raise ValueError(f"hairline: {chart}: '{column}' is infinite in row {infinite[0] + 1}; correct the value or "
                         f"leave the row out")


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
    follow in data order (flows need every node), otherwise they are left out. An empty `order` is no order."""
    names = group_names(values)
    if order is None or len(order) == 0:
        return names
    wanted = [str(name) for name in order]
    repeated = [name for name in dict.fromkeys(wanted) if wanted.count(name) > 1]
    if repeated:
        raise ValueError(f"hairline: {chart}: order names {repeated[0]!r} more than once; each group is drawn once")
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
    check_numeric(data, [value], chart)
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


def coarse_groups(data: pd.DataFrame, group: str | None, coarse: str, chart: str) -> dict[str, str]:
    """Each group's value of a coarser column (`color_by`): a group that spans two values of it cannot take one
    colour, so that is refused."""
    check_columns(data, [coarse])
    check_labels(data, [coarse], chart)
    found: dict[str, str] = {}
    labels = data[group].astype(str) if group else pd.Series([""] * len(data), index=data.index)
    for name, values in data[coarse].astype(str).groupby(labels, sort=False):
        distinct = list(dict.fromkeys(values))
        if len(distinct) > 1:
            raise ValueError(f"hairline: {chart}: color_by '{coarse}' gives '{name}' more than one value "
                             f"({', '.join(distinct[:3])}); every group needs one value of it")
        found[str(name)] = distinct[0]
    return found


def labels_with_n(names: Sequence[str], counts: Mapping[str, float], locale: str | None = None) -> list[str]:
    """'Sepsis (n = 120)': the n after the label, in the locale; colours and order keep keying on the bare name."""
    from hairline.numbers import format_number, word
    return [f"{name} ({word('n_equals', locale, n=format_number(counts[name], 0, locale))})" for name in names]


def with_caption(caption: str | None, *notes: str | None) -> str | None:
    """The caption with hairline's own notes (incomplete periods, groups not shown, hidden values) after it."""
    parts = [part for part in (caption, *notes) if part]
    return " ".join(parts) if parts else None


def partial_caption(partial: Mapping[str, str] | None, locale: str | None = None) -> str | None:
    """'Incomplete, drawn lighter: 2021 (2 months), 2026 (10 months).' in the locale."""
    from hairline.numbers import listed, word
    if not partial:
        return None
    return word("partial", locale, items=listed([f"{name} ({note})" for name, note in partial.items()]))


def check_min_n(min_n: object, chart: str) -> None:
    if min_n is not None and (isinstance(min_n, bool) or not isinstance(min_n, int) or min_n < 1):
        raise ValueError(f"hairline: {chart}: min_n must be a whole number of 1 or more; got {min_n!r}")


def drop_small(groups: list[tuple[str, np.ndarray]], min_n: int | None, chart: str,
               locale: str | None = None) -> tuple[list[tuple[str, np.ndarray]], str | None]:
    """Groups with fewer than `min_n` values are not drawn (a distribution of one value says nothing); the caption
    names them. All of them too small is an error, as an empty chart would be."""
    from hairline.numbers import format_number, listed, word
    check_min_n(min_n, chart)
    if min_n is None:
        return groups, None
    kept = [(name, values) for name, values in groups if len(values) >= min_n]
    dropped = [name for name, values in groups if len(values) < min_n]
    if not kept:
        raise ValueError(f"hairline: {chart}: every group has fewer than min_n={min_n} values; lower min_n")
    note = word("not_shown", locale, n=format_number(min_n, 0, locale), items=listed(dropped)) if dropped else None
    return kept, note


def without_small_categories(data: pd.DataFrame, category: str, min_n: int | None,
                             chart: str) -> tuple[pd.DataFrame, str | None]:
    """Rows of categories with at least `min_n` rows, and the caption note naming the others."""
    if min_n is None:
        return data, None
    check_columns(data, [category])
    counts = data.groupby(data[category].astype(str), sort=False).size()
    kept, note = drop_small([(str(name), np.ones(int(count))) for name, count in counts.items()], min_n, chart,
                            None)
    return data[data[category].astype(str).isin(dict(kept))], note


def clip_limits(values: np.ndarray, clip: float | tuple[float | None, float | None] | None,
                chart: str) -> tuple[float, float]:
    """The range drawn: everything (None), up to the `clip` quantile of every value (0.99: the top 1 % hidden), or
    between two values (`(low, high)`, either None for no limit there)."""
    if clip is None:
        return -math.inf, math.inf
    if isinstance(clip, tuple | list):
        if len(clip) != 2:
            raise ValueError(f"hairline: {chart}: clip=(low, high) takes two values; got {clip!r}")
        low, high = (-math.inf if clip[0] is None else float(clip[0]), math.inf if clip[1] is None else float(clip[1]))
        if not low < high:
            raise ValueError(f"hairline: {chart}: clip needs low below high; got {clip!r}")
        return low, high
    if isinstance(clip, bool) or not isinstance(clip, numbers.Real) or not 0 < clip < 1:
        raise ValueError(f"hairline: {chart}: clip must be a quantile between 0 and 1 (0.99) or (low, high); "
                         f"got {clip!r}")
    from hairline.stats.density import quantiles
    return -math.inf, quantiles(values, [float(clip)])[0]


def clip_caption(values: np.ndarray, limits: tuple[float, float], clip_stats: bool,
                 locale: str | None = None) -> str | None:
    """'3 values above 2,400 not drawn; the statistics use every value.' in the locale; None when none is hidden."""
    from hairline.numbers import auto_digits, count_text, format_number, word
    low, high = limits
    hidden = int(((values < low) | (values > high)).sum())
    if not hidden:
        return None
    digits = auto_digits(values)
    shown = [format_number(limit, digits, locale) for limit in (low, high)]
    where = word("outside", locale, low=shown[0], high=shown[1]) if math.isfinite(low) and math.isfinite(high) else \
        word("above", locale, limit=shown[1]) if math.isfinite(high) else word("below", locale, limit=shown[0])
    stats = word("stats_drawn" if clip_stats else "stats_every", locale)
    sentence = word("clipped", locale, values=count_text(hidden, locale), where=where, stats=stats)
    return sentence[:1].upper() + sentence[1:]


def within(values: np.ndarray, limits: tuple[float, float]) -> np.ndarray:
    return values[(values >= limits[0]) & (values <= limits[1])]


def series_colors(names: Sequence[str], data: pd.DataFrame, group: str | None, color_by: str | None,
                  colors: Mapping[str, str] | str | None, dimension: str | None, chart: str,
                  highlight: Sequence[str] | str | None = None) -> tuple[dict[str, str], dict[str, str]]:
    """Each group's colour and the legend label it stands for: its own name, or with `color_by` the coarser
    column's value (12 rows of procedure x age coloured by the 4 procedures; the palette counts the 4). Groups not
    in `highlight` take the context grey."""
    from hairline import entities
    from hairline.charts.options import highlighted
    coarse = coarse_groups(data, group, color_by, chart) if color_by else {name: name for name in names}
    palette = entities.colors_for(list(dict.fromkeys(coarse[name] for name in names)), colors, dimension)
    colours = {name: palette[coarse[name]] for name in names}
    return highlighted(colours, highlight, list(names), chart), {name: coarse[name] for name in names}
