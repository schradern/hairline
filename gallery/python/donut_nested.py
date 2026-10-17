"""Nested donut: route on the inner ring, detail on the outer ring, hierarchical key."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
discharge = data("discharge")
figure = hl.donut(discharge, None, "patients", levels=["route", "detail"], title="Discharge route and support",
                  subtitle="Inner ring: destination; outer ring: support after discharge", caption="Synthetic data.",
                  total_label="patients")
finish(figure, "donut_nested")
