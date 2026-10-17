# Dot plot with intervals: ICU mortality per unit with 95 % intervals, sorted by value.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_dotplot(gallery_data("rates"), "unit", "mortality", "low", "high", title = "ICU mortality by unit",
                   subtitle = "Share of patients who died in the ICU, 2025", caption = "Synthetic data. Wald intervals.")
finish(plot, "dotplot_rates", "double")
