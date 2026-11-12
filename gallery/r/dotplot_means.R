# A dot plot of means with their 95% CI, summarised from one row per patient; n after each unit.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_dotplot(gallery_data("stays"), "unit", "days", title = "Mean length of ICU stay by unit",
                   subtitle = "Days from admission to discharge, 2025", caption = "Synthetic data.",
                   summary = c("mean", "ci"), x_title = "Days")
finish(plot, "dotplot_means", "onehalf")
