# Comparisons as numbers: each unit's shift against the surgical unit with its 95% CI and p, beside the rows.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_spread(gallery_data("stays"), "unit", "days", title = "Length of ICU stay against the surgical unit",
                  subtitle = "Days from admission to discharge, 2025", caption = "Synthetic data.",
                  stats = c("median", "n"), compare = "Surgical", numbers = "right", x_title = "Days")
finish(plot, "spread_compare", "double")
