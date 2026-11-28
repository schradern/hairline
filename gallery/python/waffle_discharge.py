"""Waffle chart: where patients went after the ICU, one cell per percent."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.waffle(data("discharge"), "route", "patients", title="Discharge route",
                   subtitle="Share of 754 patients leaving the ICU, 2025", caption="Synthetic data.")
finish(figure, "waffle_discharge")
