"""The fictional example brand: readable brand colours, German number format."""

from pathlib import Path

import hairline as hl

from common import data, finish

hl.use(brand=Path(__file__).resolve().parents[2] / "brands" / "example" / "_brand.yml")
points = data("scatter")
figure = hl.figure("Lactate by risk group", subtitle="Example University Hospital design", caption="Synthetic data.",
                   size="onehalf")
for group in ["Low risk", "Medium risk", "High risk"]:
    subset = points[points["group"] == group]
    figure.ax.scatter(subset["sofa"], subset["lactate"], label=group)
figure.legend()
figure.y_title("Lactate")
finish(figure, "brand_example")
