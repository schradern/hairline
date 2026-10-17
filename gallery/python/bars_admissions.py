"""Bar chart from raw rows: admissions counted per diagnosis, women and men side by side."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.bars(data("admissions"), "diagnosis", by="sex", subtitle="Admissions to all ICUs, 2025",
                 caption="Synthetic data.", size="double")
finish(figure, "bars_admissions")
