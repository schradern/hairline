# Partition bars: the same hierarchy as the nested donut, read top to bottom.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_partition(gallery_data("discharge"), c("route", "detail"), "patients", title = "Discharge route and support",
                     subtitle = "Share of 754 patients leaving the ICU, 2025", caption = "Synthetic data.",
                     level_names = c("Destination", "Support after discharge"))
finish(plot, "partition_discharge", "double")
