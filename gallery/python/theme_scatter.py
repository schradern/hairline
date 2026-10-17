"""Single panel: scatter with three groups, axis titles, legend row and caption."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
points = data("scatter")
figure = hl.figure("Lactate and SOFA score at admission", subtitle="One dot per patient, three risk groups",
                   caption="Synthetic data. Lactate in mmol/l.", size="onehalf")
for group in ["Low risk", "Medium risk", "High risk"]:
    subset = points[points["group"] == group]
    figure.ax.scatter(subset["sofa"], subset["lactate"], label=group)
figure.legend()
figure.y_title("Lactate")
figure.x_title("SOFA score")
finish(figure, "theme_scatter")
