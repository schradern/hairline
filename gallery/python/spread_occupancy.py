"""Spread rows: occupied beds per unit at midnight, range, interquartile band and median, capacity as a tick."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
occupancy = data("occupancy")
occupancy["occupied"] = (occupancy["share"] * occupancy["beds"]).round()
capacity = occupancy.groupby("ward")["beds"].first().to_dict()
figure = hl.spread(occupancy, "ward", "occupied", marks=capacity, mark_label="beds", zero=True,
                   axis_title="Occupied beds at 00:00", title="Occupied beds by unit",
                   subtitle="Every day, January 2025 to June 2026; ticks mark the capacity", caption="Synthetic data.",
                   size="double")
finish(figure, "spread_occupancy")
