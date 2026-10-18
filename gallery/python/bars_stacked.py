"""Stacked bars from raw rows: admissions per diagnosis, women and men stacked, totals at the ends."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.bars(data("admissions"), "diagnosis", by="sex", stacked=True, horizontal=False,
                 title="Admissions by diagnosis and sex",
                 subtitle="Admissions to all ICUs, 2025", caption="Synthetic data.", size="double")
finish(figure, "bars_stacked")
