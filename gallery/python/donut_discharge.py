"""Single-ring donut: labels outside with leader lines, total in the centre."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
discharge = data("discharge")
figure = hl.donut(discharge, "route", "patients", title="Where patients go after the ICU",
                  subtitle="Discharge destination, all ICUs, 2025", caption="Synthetic data.", total_label="patients")
finish(figure, "donut_discharge")
