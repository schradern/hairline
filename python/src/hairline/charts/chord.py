"""Chord diagram: groups on a ring, ribbons joining each pair, width by the value at both ends."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

from hairline import entities
from hairline.charts.chord_geometry import chord_drawing
from hairline.charts.common import flow_rows, humanise, with_counts
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.numbers import auto_digits, format_number
from hairline.settings import current_settings


def chord_spec(data: pd.DataFrame, source: str, target: str, value: str | None = None, *,
               order: Sequence[str] | None = None, colors: Mapping[str, str] | None = None) -> dict:
    """One link per pair (both directions combined), groups with their totals and colours by count."""
    data, value = with_counts(data, value)
    rows, names = flow_rows(data, source, target, value, "chord", order)
    totals: dict[tuple[str, str], float] = {}
    for first, second, amount in zip(rows[source].astype(str), rows[target].astype(str), rows[value], strict=True):
        if first != second:
            key = (first, second) if names.index(first) <= names.index(second) else (second, first)
            totals[key] = totals.get(key, 0.0) + float(amount)
    links = [{"source": first, "target": second, "value": amount} for (first, second), amount in totals.items()
             if amount > 0]
    locale, palette = current_settings().locale, entities.colors_for(names, colors)
    flows = {name: sum(link["value"] for link in links if name in (link["source"], link["target"])) for name in names}
    digits = auto_digits([link["value"] for link in links])
    nodes = [{"name": name, "value": flows[name], "value_text": format_number(flows[name], digits, locale),
              "color": palette[name]} for name in names if flows[name] > 0]
    return {"nodes": nodes, "links": links}


def chord(data: pd.DataFrame, source: str, target: str, value: str | None = None, *, title: str | None = None,
          subtitle: str | None = None, caption: str | None = None, order: Sequence[str] | None = None,
          colors: Mapping[str, str] | None = None, size: str = "onehalf") -> HairlineFigure:
    """Exchanges between groups on a ring; without `value` each row counts once."""
    spec = chord_spec(data, source, target, value, order=order, colors=colors)
    label = humanise(value) if value else "Count"
    result = figure(title or f"{label} between {str(source).replace('_', ' ')} and {str(target).replace('_', ' ')}",
                    subtitle=subtitle, caption=caption, size=size)
    result.draw(0, lambda box, measure, style: chord_drawing(spec, box, measure, style))
    return fit_height(result, shrink=False)
