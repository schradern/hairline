# Summary marks and numbers: the median, mean, IQR and range at each box, their numbers under the groups.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_raincloud(gallery_data("stays"), "unit", "days", title = "Length of ICU stay by unit",
                     subtitle = "Days from admission to discharge, 2025", y_title = "Days",
                     caption = "Synthetic data.", summary = c("median", "mean", "iqr", "range"),
                     stats = c("median", "iqr", "mean", "ci"))
finish(plot, "raincloud_means", "double")
