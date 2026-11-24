"""Spread rows with written columns: operating time drawn per ASA class, age and length of stay beside it."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.spread(data("surgery"), "asa", "duration", stats=("median", "iqr", "n"), order=["ASA I", "ASA II",
                                                                                           "ASA III", "ASA IV"],
                   columns={"age": "Age (years)", "stay": "Stay (days)"}, axis_title="Minutes",
                   title="Operating time by ASA class", subtitle="Elective operations, 2022 to 2024",
                   caption="Synthetic data.", size="double")
finish(figure, "spread_columns")
