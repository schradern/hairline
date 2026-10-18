"""Ridgeline from raw rows: age at admission per diagnosis, one ridge each on a shared age axis."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.ridgeline(data("ages"), "diagnosis", "age", title="Age at admission by diagnosis",
                      subtitle="540 ICU admissions, 2025; lines mark the medians", caption="Synthetic data.",
                      size="double")
finish(figure, "ridgeline_ages")
