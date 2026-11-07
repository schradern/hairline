# Spread rows in sections: the rated usefulness of each feature of a patient portal, by area, the mean as an open
# diamond beside the median, rows sorted by median.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_spread(gallery_data("importance"), "feature", "rating", section = "area", panel_letters = TRUE,
                  color_by = "area", mean = TRUE, sort = "median", stats = c("median", "iqr", "n"), discrete = TRUE,
                  axis_title = "Rated usefulness, 1 (not useful) to 10 (essential)",
                  title = "What patients want from the portal", subtitle = "Rated usefulness of each feature",
                  caption = "Synthetic data.")
finish(plot, "spread_importance", "double")
