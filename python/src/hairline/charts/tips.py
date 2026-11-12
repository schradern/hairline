"""Interactive tags for drawn shapes: the series a shape belongs to, its tooltip, and where the tooltip points
(the middle point of a line, the centroid of a polygon). Pure; mirrored in R's tagged_shape()."""

from __future__ import annotations

from hairline.numbers import auto_digits, format_number


def anchor(shape: dict) -> list[float]:
    points = shape["points"]
    if shape["kind"] == "line":
        return list(points[len(points) // 2])
    return [sum(point[0] for point in points) / len(points), sum(point[1] for point in points) / len(points)]


def tagged(shape: dict, series: str, tip: str) -> dict:
    return {**shape, "series": series, "tip": tip, "tip_at": anchor(shape)}


def pairs_tip(name: str, pairs) -> str:
    """A row's key numbers as its tooltip, as the numbers beside it read: 'Unit A: Median 4.2, n 64'."""
    return f"{name}: " + ", ".join(f"{label} {value}" for label, value in pairs)


def tip_measures(marks, stats) -> tuple[str, ...]:
    """The measures a group's tooltip lists: the marks drawn, then the numbers written, then its n."""
    return tuple(dict.fromkeys([*marks, *stats, "n"]))


def amount_text(value: float) -> str:
    """An amount with the shared digits rule (whole numbers whole)."""
    return format_number(value, auto_digits([value]))
