# Single-ring donut: labels outside with leader lines, total in the centre.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
discharge <- gallery_data("discharge")
plot <- hl_donut(discharge, "route", "patients", title = "Where patients go after the ICU",
                 subtitle = "Discharge destination, all ICUs, 2025", caption = "Synthetic data.",
                 total_label = "patients")
finish(plot, "donut_discharge", "onehalf")
