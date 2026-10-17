"""Funnel plot: odds ratios against their standard error, pseudo 95 % limits, Egger's test computed."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.funnel(data("funnel"), "odds_ratio", "se", subtitle="Fourteen trials of early mobilisation",
                   caption="Synthetic data. Inverse-variance pooled estimate.", size="double")
finish(figure, "funnel_trials")
