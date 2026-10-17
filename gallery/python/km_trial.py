"""Kaplan–Meier curves with confidence bands, censor ticks, medians and the number at risk."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.kaplan_meier(data("trial"), "months", "died", by="arm", order=["Standard care", "Early mobilisation"],
                         title="Survival after ICU discharge", subtitle="Kaplan–Meier estimate with 95 % bands",
                         caption="Synthetic data. Hazard ratio from a Cox model, log-rank test.",
                         x_title="Months since discharge", endpoint="Overall survival",
                         stats=[("HR", "0.62 [0.44, 0.88]"), ("Log-rank p", "0.007")], size="double")
finish(figure, "km_trial")
