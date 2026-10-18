# Ridgeline from raw rows: age at admission per diagnosis, one ridge each on a shared age axis.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_ridgeline(gallery_data("ages"), "diagnosis", "age", title = "Age at admission by diagnosis",
                     subtitle = "540 ICU admissions, 2025; lines mark the medians", caption = "Synthetic data.")
finish(plot, "ridgeline_ages", "double")
