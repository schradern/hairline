"""Correlation heatmap: every numeric column of a patient table, lower triangle, values in the cells."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
patients = data("patients").rename(columns={"sofa": "SOFA score"})
figure = hl.correlation(patients, subtitle="Measurements at ICU admission, 160 patients", caption="Synthetic data.",
                        size="double")
finish(figure, "correlation_patients")
