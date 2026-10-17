"""Dot plot with intervals: ICU mortality per unit with 95 % intervals, sorted by value."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.dotplot(data("rates"), "unit", "mortality", "low", "high", title="ICU mortality by unit",
                    subtitle="Share of patients who died in the ICU, 2025", caption="Synthetic data. Wald intervals.",
                    size="double")
finish(figure, "dotplot_rates")
