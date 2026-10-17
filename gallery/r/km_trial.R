# Kaplan–Meier curves with confidence bands, censor ticks, medians and the number at risk.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_kaplan_meier(gallery_data("trial"), "months", "died", by = "arm",
                        order = c("Standard care", "Early mobilisation"), title = "Survival after ICU discharge",
                        subtitle = "Kaplan–Meier estimate with 95 % bands",
                        caption = "Synthetic data. Hazard ratio from a Cox model, log-rank test.",
                        x_title = "Months since discharge", endpoint = "Overall survival",
                        stats = c(HR = "0.62 [0.44, 0.88]", `Log-rank p` = "0.007"))
finish(plot, "km_trial", "onehalf")
