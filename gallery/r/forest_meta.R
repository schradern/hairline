# Forest plot: results table, weighted squares, pooled diamond, log axis and favours labels.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_forest(gallery_data("meta"), "study", "or", "low", "high", weight = "weight",
                  columns = c("Events / n" = "events"),
                  pooled = list(estimate = 0.72, low = 0.58, high = 0.89, label = "Random effects"),
                  favours = c("Favours early mobilisation", "Favours standard care"), effect_heading = "OR [95 % CI]",
                  title = "Early mobilisation and 90-day mortality",
                  subtitle = "Odds ratios from five randomised trials",
                  heterogeneity = "I\u00b2 = 18 %, tau\u00b2 = 0.01, p = 0.30", caption = "Synthetic data.")
finish(plot, "forest_meta", "double")
