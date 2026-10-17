"""Correlation heatmap: every numeric column of a patient table, lower triangle, values in the cells."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.correlation(data("patients"), subtitle="Measurements at ICU admission, 160 patients",
                        caption="Synthetic data.", size="double")
finish(figure, "correlation_patients")
