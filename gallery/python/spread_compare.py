"""Comparisons as numbers: each unit's shift against the surgical unit with its 95 % CI and p, beside the rows."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.spread(data("stays"), "unit", "days", title="Length of ICU stay against the surgical unit",
                   subtitle="Days from admission to discharge, 2025", caption="Synthetic data.",
                   stats=("median", "n"), compare="Surgical", numbers="right", x_title="Days", size="double")
finish(figure, "spread_compare")
