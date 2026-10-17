"""Raincloud: half densities, boxes and points per unit, n under the groups, test results as brackets."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.raincloud(data("stays"), "unit", "days", title="Length of ICU stay by unit",
                      subtitle="Days from admission to discharge, 2025", y_title="Days",
                      caption="Synthetic data. p from Wilcoxon rank-sum tests.",
                      comparisons=[("Surgical", "Medical", "p = 0.004"), ("Medical", "Neuro", "p = 0.08"),
                                   ("Surgical", "Neuro", "p < 0.001")], size="double")
finish(figure, "raincloud_stay")
