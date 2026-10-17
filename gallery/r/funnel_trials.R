# Funnel plot: odds ratios against their standard error, pseudo 95 % limits, Egger's test computed.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_funnel(gallery_data("funnel"), "odds_ratio", "se", subtitle = "Fourteen trials of early mobilisation",
                  caption = "Synthetic data. Inverse-variance pooled estimate.")
finish(plot, "funnel_trials", "double")
