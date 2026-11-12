"""A dot plot of means with their 95 % CI, summarised from one row per patient; n after each unit."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.dotplot(data("stays"), "unit", "days", title="Mean length of ICU stay by unit",
                    subtitle="Days from admission to discharge, 2025", caption="Synthetic data.",
                    summary=("mean", "ci"), x_title="Days", size="onehalf")
finish(figure, "dotplot_means")
