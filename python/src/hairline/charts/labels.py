"""Label placement shared by the chart types: push overlapping labels apart along one direction."""

from __future__ import annotations

from collections.abc import Sequence


def isotonic(values: Sequence[float]) -> list[float]:
    """Closest non-decreasing sequence in the least-squares sense (pool adjacent violators)."""
    blocks: list[list[float]] = []
    for value in values:
        blocks.append([value, 1.0])
        while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]:
            total, count = blocks.pop()
            blocks[-1][0] += total
            blocks[-1][1] += count
    return [total / count for total, count in blocks for _ in range(int(count))]


def spread_labels(positions: Sequence[float], height: float, low: float, high: float) -> list[float]:
    """Label centres at least `height` apart, as close to `positions` as possible, within [low, high].

    Returned in input order; labels that cannot all fit are centred on the available range.
    """
    order = sorted(range(len(positions)), key=lambda index: (positions[index], index))
    shifted = isotonic([positions[index] - rank * height for rank, index in enumerate(order)])
    floor, ceiling = low, high - (len(positions) - 1) * height
    if ceiling < floor:
        shifted = [(floor + ceiling) / 2] * len(shifted)
    else:
        shifted = [min(max(value, floor), ceiling) for value in shifted]
    result = [0.0] * len(positions)
    for rank, index in enumerate(order):
        result[index] = shifted[rank] + rank * height
    return result
