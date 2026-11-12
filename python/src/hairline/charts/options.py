"""Options every chart shares, applied the same way wherever they appear: axis titles, reference lines, highlighted
series, a title for the legend row and the order of groups. A chart offers an option by passing it here; the R
package mirrors each function in chart_options.R."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from hairline.figure import HairlineFigure

Reference = float | tuple[float, str] | Sequence[float | tuple[float, str]] | Mapping[str, float] | None
GROUP_SORTS = ("median", "mean", "n")
# Where row charts (spread, dot plot) write their numbers: beside the plot while it keeps its least width, else under
# each row ("auto"); always beside it ("right"), or always under each row ("below").
NUMBER_PLACES = ("auto", "right", "below")


def references(reference: Reference, chart: str) -> list[tuple[float, str | None]]:
    """A reference value, (value, label), a list of them or {label: value}, as (value, label) pairs."""
    if reference is None:
        return []
    if isinstance(reference, Mapping):
        reference = [(value, label) for label, value in reference.items()]
    single = isinstance(reference, (int, float)) or (isinstance(reference, tuple) and len(reference) == 2
                                                     and isinstance(reference[1], str))
    found = []
    for item in [reference] if single else list(reference):
        value, label = item if isinstance(item, tuple) else (item, None)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"hairline: {chart}: reference {item!r} must be a number or (number, label)")
        found.append((float(value), None if label is None else str(label)))
    return found


def checked_highlight(highlight: Sequence[str] | str | None, names: Sequence[str], chart: str) -> list[str] | None:
    """The series to keep in colour, each one of the chart's groups."""
    if highlight is None:
        return None
    chosen = [highlight] if isinstance(highlight, str) else [str(name) for name in highlight]
    unknown = [name for name in chosen if name not in names]
    if unknown:
        raise ValueError(f"hairline: {chart}: highlight names {unknown[0]!r}, which is not a group; groups: "
                         f"{', '.join(names)}")
    return chosen


def highlighted(palette: Mapping[str, str], highlight: Sequence[str] | str | None, names: Sequence[str],
                chart: str) -> dict[str, str]:
    """Group colours with every group not highlighted in the context grey, for charts that colour by group."""
    chosen = checked_highlight(highlight, names, chart)
    if not chosen:
        return dict(palette)
    from hairline.marks import context_color
    from hairline.settings import current_settings
    grey = context_color(current_settings())
    return {name: color if name in chosen else grey for name, color in palette.items()}


def apply_options(result: HairlineFigure, chart: str, *, names: Sequence[str] = (), x_title: str | None = None,
                  y_title: str | None = None, reference: Reference = None, reference_axis: str = "y",
                  highlight: Sequence[str] | str | None = None, key_title: str | None = None) -> HairlineFigure:
    """Axis titles, reference lines on the value axis (`reference_axis`), highlighted groups and the legend title,
    for a chart drawn on matplotlib axes."""
    if x_title:
        result.x_title(x_title)
    if y_title:
        result.y_title(y_title)
    for value, label in references(reference, chart):
        result.reference(**{reference_axis: value}, label=label)
    chosen = checked_highlight(highlight, names, chart)
    if chosen:
        result.highlight(series=chosen)
    if key_title:
        result.key_title(key_title)
    return result


def check_numbers(numbers: str, chart: str) -> str:
    if numbers not in NUMBER_PLACES:
        raise ValueError(f"hairline: {chart}: numbers {numbers!r} must be one of {', '.join(map(repr, NUMBER_PLACES))}")
    return numbers


def numbers_beside(place: str, plot: float, least: float, base: float, chart: str) -> bool:
    """Whether a row chart's numbers sit beside a plot `plot` pt wide: by `place`, and with "right" only while the
    plot keeps `spacing.min_plot_beside`; narrower, the figure stops and says what would fit."""
    from hairline.errors import HairlineLayoutError
    from hairline.tokens import load_tokens
    if place == "below":
        return False
    if place == "auto":
        return plot >= least
    floor = load_tokens()["spacing"]["min_plot_beside"] * base
    if plot < floor:
        raise HairlineLayoutError(f"hairline: {chart}: the numbers beside the plot leave it {max(plot, 0):.0f} pt, "
                                  f"and it needs {floor:.0f} pt; use a wider size, show fewer numbers, or "
                                  f"numbers='auto' (under each row where the plot would be too narrow)")
    return True


def check_sort(sort: str | None, allowed: Sequence[str], chart: str) -> None:
    if sort is not None and sort not in allowed:
        raise ValueError(f"hairline: {chart}: sort {sort!r} must be one of {', '.join(map(repr, allowed))} or None "
                         f"(the given order)")


def sort_key(values: np.ndarray, sort: str) -> float:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if sort == "n":
        return float(len(values))
    if not len(values):
        return -math.inf
    return float(np.median(values) if sort == "median" else np.mean(values))


def sorted_groups(groups: list, sort: str | None, chart: str,
                  values_of: Callable[[object], np.ndarray] = lambda values: values) -> list:
    """(name, values) groups, highest median, mean or n first; None keeps the given order. Ties keep it too."""
    check_sort(sort, GROUP_SORTS, chart)
    if sort is None:
        return groups
    return sorted(groups, key=lambda group: -sort_key(values_of(group[1]), sort))

def reference_line_height(spec: dict, style: dict) -> float:
    """Charts that draw their own shapes (spread, dot plot, Likert): a line above the rows for the reference labels,
    when a reference has one."""
    from hairline.charts.donut_geometry import line_height
    return line_height(style, "caption") if any(label for _, label in spec.get("references", [])) else 0.0


def reference_shapes(spec: dict, scale, top: float, bottom: float, style: dict) -> list[dict]:
    """Each reference as a dashed line across the rows, its label above them, right of the line, as a reference
    line on any other chart."""
    from hairline.charts.donut_geometry import baseline_for, text
    from hairline.tokens import load_tokens
    rules = load_tokens()["reference"]
    above = reference_line_height(spec, style)
    baseline = baseline_for(top + above / 2, style, "caption")
    shapes = []
    for value, label in spec.get("references", []):
        x = scale(value)
        shapes.append({"kind": "line", "points": [[x, top + above], [x, bottom]], "color": rules["color"],
                       "width": style["leader_width"], "dash": rules["dash"], "role": "reference"})
        if label:
            shapes.append(text(x + rules["label_gap"] * style["sizes"]["caption"], baseline, label, "caption",
                               style["neutral"]["faint"]))
    return shapes


FACET_KEY, FACET_BLOCK = "_hairline_facet_key", "_hairline_facet_block"


def facet_rows(data, group: str, facet: str, order: Sequence[str] | None, chart: str):
    """For charts that draw facets as blocks of rows on one axis (spread, Likert, dot plot): each row keyed by its
    facet and group ("2025 · Unit A", the name a caption uses), blocks in the order the facet's values first
    appear, groups in `order` within each. Returns the data with the key and block columns, the keys in order and
    each key's group."""
    from hairline.charts.common import check_columns, check_labels, ordered_names
    check_columns(data, [group, facet])
    check_labels(data, [facet], chart)
    names = ordered_names(data[group], order, chart, group)
    data = data[data[group].astype(str).isin(names)]
    keyed = data.assign(**{FACET_KEY: data[facet].astype(str) + " · " + data[group].astype(str),
                           FACET_BLOCK: data[facet].astype(str)})
    blocks = list(dict.fromkeys(keyed[FACET_BLOCK]))
    present = set(keyed[FACET_KEY])
    keys = [f"{block} · {name}" for block in blocks for name in names if f"{block} · {name}" in present]
    return keyed, keys, {key: key.split(" · ", 1)[1] for key in keys}
