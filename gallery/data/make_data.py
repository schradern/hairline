"""Synthetic gallery data with the character of the reference figures (no patient data)."""

from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np

SEED = 20260717
FOLDER = Path(__file__).resolve().parent
MAX_OCCUPANCY = 1.15  # overflow beds: real ICU occupancy rarely passes about 110 %
WARDS = [("Unit A", 0.60, 24), ("Unit B", 0.86, 12), ("Unit C", 0.69, 12), ("Unit D", 0.79, 12),
         ("Unit E", 0.79, 11), ("Unit F", 0.68, 10)]
DAYS = 546
INTERIM = (120, 485)


def occupancy_rows(rng: np.random.Generator) -> list[dict]:
    rows = []
    for ward, level, beds in WARDS:
        drift, values = 0.0, []
        for day in range(DAYS):
            drift = 0.9 * drift + rng.normal(0, 0.035)
            weekly = 0.04 * math.sin(day / 7 * 2 * math.pi)
            values.append(min(MAX_OCCUPANCY, max(0.15, level + drift + weekly + rng.normal(0, 0.06))))
        smooth = np.convolve(values, np.ones(7) / 7, mode="full")[:DAYS]
        smooth[:6] = [np.mean(values[: index + 1]) for index in range(6)]
        interim = ward in ("Unit B", "Unit D")
        for day in range(DAYS):
            rows.append({"ward": ward, "day": day, "share": round(values[day], 5), "mean7": round(smooth[day], 5),
                         "beds": beds - 2 if interim and INTERIM[0] <= day <= INTERIM[1] else beds})
    return rows


def scatter_rows(rng: np.random.Generator) -> list[dict]:
    rows = []
    for group, offset in (("Low risk", 0.0), ("Medium risk", 0.8), ("High risk", 1.6)):
        for _ in range(48):
            sofa = rng.uniform(2, 14)
            rows.append({"group": group, "sofa": round(sofa, 3),
                         "lactate": round(max(0.4, 0.6 + offset + 0.25 * sofa + rng.normal(0, 0.7)), 3)})
    return rows


def write(name: str, rows: list[dict]) -> None:
    with (FOLDER / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rng = np.random.default_rng(SEED)
    write("occupancy.csv", occupancy_rows(rng))
    write("scatter.csv", scatter_rows(rng))


if __name__ == "__main__":
    main()
