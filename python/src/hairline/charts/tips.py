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


def amount_text(value: float) -> str:
    """An amount with the shared digits rule (whole numbers whole)."""
    return format_number(value, auto_digits([value]))
