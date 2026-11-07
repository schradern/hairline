"""Scatter with a linear fit and its 95 % band; n, r and slope as key numbers."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
patients = data("scatter").rename(columns={"sofa": "SOFA score", "lactate": "Lactate (mmol/l)"})
figure = hl.scatter(patients, "SOFA score", "Lactate (mmol/l)", by="group",
                    order=["Low risk", "Medium risk", "High risk"], colors="oranges",
                    title="Lactate rises with the SOFA score", subtitle="One dot per patient at admission",
                    caption="Synthetic data.", size="double")
finish(figure, "scatter_fit")
