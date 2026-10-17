"""Arc diagram from raw rows: patient moves along a care pathway, counted per pair, width by count."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
stages = ["Emergency", "Theatre", "ICU", "Step-down", "Ward", "Rehabilitation", "Home"]
figure = hl.arcs(data("pathways"), "origin", "destination", order=stages, title="Moves along the care pathway",
                 subtitle="420 patient moves, 2025", caption="Synthetic data.", size="double")
finish(figure, "arcs_pathways")
