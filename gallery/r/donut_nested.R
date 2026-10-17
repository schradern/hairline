# Nested donut: route on the inner ring, detail on the outer ring, hierarchical key.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
discharge <- gallery_data("discharge")
plot <- hl_donut(discharge, NULL, "patients", levels = c("route", "detail"), title = "Discharge route and support",
                 subtitle = "Inner ring: destination; outer ring: support after discharge", caption = "Synthetic data.",
                 total_label = "patients")
finish(plot, "donut_nested", "double")
