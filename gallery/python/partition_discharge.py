"""Partition bars: the same hierarchy as the nested donut, read top to bottom."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.partition(data("discharge"), ["route", "detail"], "patients", title="Discharge route and support",
                      subtitle="Share of 754 patients leaving the ICU, 2025", caption="Synthetic data.",
                      level_names=["Destination", "Support after discharge"], size="double")
finish(figure, "partition_discharge")
