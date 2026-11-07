"""Facets as blocks of rows: occupied beds per unit, a block per year on one axis, the planned staffing level as a
labelled reference and one unit highlighted, all options every chart shares."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
occupancy = data("occupancy")
occupancy["occupied"] = (occupancy["share"] * occupancy["beds"]).round()
occupancy["year"] = (2025 + occupancy["day"] // 365).astype(str)
figure = hl.spread(occupancy, "ward", "occupied", facet="year", highlight=["Unit B"], reference={"Planned": 10},
                   x_title="Occupied beds at 00:00", stats=("median", "iqr"), title="Unit B stays above plan",
                   subtitle="Occupied beds per day, 2025 and the first half of 2026", caption="Synthetic data.",
                   size="double")
finish(figure, "spread_years")
