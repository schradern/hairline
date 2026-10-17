# Raincloud: half densities, boxes and points per unit, n under the groups, test results as brackets.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_raincloud(gallery_data("stays"), "unit", "days", title = "Length of ICU stay by unit",
                     subtitle = "Days from admission to discharge, 2025", y_title = "Days",
                     caption = "Synthetic data. p from Wilcoxon rank-sum tests.",
                     comparisons = list(c("Surgical", "Medical", "p = 0.004"), c("Medical", "Neuro", "p = 0.08"),
                                        c("Surgical", "Neuro", "p < 0.001")))
finish(plot, "raincloud_stay", "double")
