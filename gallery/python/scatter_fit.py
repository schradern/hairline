"""Scatter with a linear fit and its 95 % band; n, r and slope as key numbers."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.scatter(data("scatter"), "sofa", "lactate", by="group", title="Lactate rises with the SOFA score",
                    subtitle="One dot per patient at admission", caption="Synthetic data. Lactate in mmol/l.",
                    size="double")
finish(figure, "scatter_fit")
