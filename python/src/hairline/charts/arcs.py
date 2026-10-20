"""Arc diagram: nodes on a baseline, arcs above joining each pair, width by value, one hue."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from hairline.charts.arcs_geometry import arcs_drawing
from hairline.charts.common import flow_rows, humanise, with_counts
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.marks import lone_color
from hairline.numbers import auto_digits, format_number
from hairline.settings import current_settings


def arcs_spec(data: pd.DataFrame, source: str, target: str, value: str | None,
              order: Sequence[str] | None = None) -> dict:
    """Nodes in order of first appearance (or `order`) and one link per pair with its summed value."""
    data, value = with_counts(data, value)
    rows, names = flow_rows(data, source, target, value, "arcs", order)
    totals: dict[tuple[str, str], float] = {}
    directions: dict[tuple[str, str], set] = {}
    for first, second, amount in zip(rows[source].astype(str), rows[target].astype(str), rows[value], strict=True):
        # An arc has no direction: A → B and B → A share one arc, so they add up rather than overlap.
        key = (first, second) if names.index(first) <= names.index(second) else (second, first)
        totals[key] = totals.get(key, 0.0) + float(amount)
        directions.setdefault(key, set()).add((first, second))
    amounts = [amount for amount in totals.values() if amount > 0]
    locale, digits = current_settings().locale, auto_digits(amounts)
    links = [{"source": first, "target": second, "value": amount,
              "value_text": format_number(amount, digits, locale), "pair": pair_text(directions[(first, second)])}
             for (first, second), amount in totals.items() if amount > 0]
    return {"nodes": names, "links": links, "color": lone_color(), "key": arcs_key(amounts, digits, locale)}


def pair_text(directions: set) -> str:
    """'A → B' for one direction, 'A ↔ B' when the arc carries both."""
    (first, second), *rest = sorted(directions)
    return f"{first} ↔ {second}" if rest else f"{first} → {second}"


def arcs_key(amounts: list[float], digits: int, locale: str) -> list[dict]:
    """Key widths for the largest link, half of it and the smallest, each once and above zero, in the data's
    decimals (half of a largest link of 1 is 0.5, not 0)."""
    largest = max(amounts)
    half = round(largest / 2, digits)
    shown = sorted({value for value in (largest, half, min(amounts)) if value > 0})
    return [{"value": value, "text": format_number(value, digits, locale)} for value in shown]


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
