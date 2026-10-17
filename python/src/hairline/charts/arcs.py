"""Arc diagram: nodes on a baseline, arcs above joining each pair, width by value, one hue."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from hairline.charts.arcs_geometry import arcs_drawing
from hairline.charts.common import check_columns, humanise, with_counts
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.numbers import format_number
from hairline.settings import current_settings


def arcs_spec(data: pd.DataFrame, source: str, target: str, value: str | None,
              order: Sequence[str] | None = None) -> dict:
    """Nodes in order of first appearance (or `order`) and one link per pair with its summed value."""
    data, value = with_counts(data, value)
    check_columns(data, [source, target, value])
    names = list(order) if order else list(dict.fromkeys([str(name) for pair in zip(data[source], data[target],
                                                                                     strict=True) for name in pair]))
    totals: dict[tuple[str, str], float] = {}
    for _, row in data.iterrows():
        key = (str(row[source]), str(row[target]))
        totals[key] = totals.get(key, 0.0) + float(row[value])
    locale = current_settings().locale
    links = [{"source": first, "target": second, "value": amount, "value_text": format_number(amount, 0, locale)}
             for (first, second), amount in totals.items() if first != second and amount > 0]
    largest = max(link["value"] for link in links)
    return {"nodes": names, "links": links, "color": current_settings().palette[0],
            "key": [{"value": amount, "text": format_number(amount, 0, locale)}
                    for amount in sorted({largest, round(largest / 2), min(link["value"] for link in links)})]}


def arcs(data: pd.DataFrame, source: str, target: str, value: str | None = None, *, title: str | None = None,
         subtitle: str | None = None, caption: str | None = None, order: Sequence[str] | None = None,
         size: str = "onehalf") -> HairlineFigure:
    """Flows between nodes as arcs above a baseline; without `value` each row counts once."""
    spec = arcs_spec(data, source, target, value, order)
    label = humanise(value) if value else "Count"
    result = figure(title or f"{label} from {str(source).replace('_', ' ')} to {str(target).replace('_', ' ')}",
                    subtitle=subtitle, caption=caption, size=size)
    result.draw(0, lambda box, measure, style: arcs_drawing(spec, box, measure, style))
    return fit_height(result)
