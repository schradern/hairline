# Waffle chart: where patients went after the ICU, one cell per percent.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_waffle(gallery_data("discharge"), "route", "patients", title = "Discharge route",
                  subtitle = "Share of 754 patients leaving the ICU, 2025", caption = "Synthetic data.")
finish(plot, "waffle_discharge", "onehalf")
