"""Venn diagram from membership columns: diabetes, hypertension and obesity among ICU patients."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.venn(data("comorbidities"), ["diabetes", "hypertension", "obesity"],
                 title="Diabetes, hypertension and obesity", subtitle="600 ICU patients, 2025",
                 caption="Synthetic data.", size="double")
finish(figure, "venn_comorbidities")
