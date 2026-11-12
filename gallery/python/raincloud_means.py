"""Summary marks and numbers: the median, mean, IQR and range at each box, their numbers under the groups."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.raincloud(data("stays"), "unit", "days", title="Length of ICU stay by unit",
                      subtitle="Days from admission to discharge, 2025", y_title="Days",
                      caption="Synthetic data.", summary=("median", "mean", "iqr", "range"),
                      stats=("median", "iqr", "mean", "ci"), size="double")
finish(figure, "raincloud_means")
