"""Risk-of-bias summary from a wide table: one column per domain, judgements as written by reviewers."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
domains = ["Randomisation", "Deviations", "Missing data", "Measurement", "Reporting"]
figure = hl.risk_of_bias(data("bias"), "study", domains=domains, subtitle="Twelve trials, RoB 2 domains",
                         caption="Synthetic data. Overall: each trial's worst domain.", size="double")
finish(figure, "risk_of_bias_trials")
