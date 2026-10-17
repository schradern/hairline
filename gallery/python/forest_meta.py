"""Forest plot: results table, weighted squares, pooled diamond, log axis and favours labels."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.forest(data("meta"), "study", "or", "low", "high", weight="weight", columns={"Events / n": "events"},
                   pooled={"estimate": 0.72, "low": 0.58, "high": 0.89, "label": "Random effects"},
                   favours=("Favours early mobilisation", "Favours standard care"), effect_heading="OR [95 % CI]",
                   title="Early mobilisation and 90-day mortality", subtitle="Odds ratios from five randomised trials",
                   heterogeneity="I² = 18 %, tau² = 0.01, p = 0.30", caption="Synthetic data.")
finish(figure, "forest_meta")
