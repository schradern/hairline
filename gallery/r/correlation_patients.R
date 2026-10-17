# Correlation heatmap: every numeric column of a patient table, lower triangle, values in the cells.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_correlation(gallery_data("patients"), subtitle = "Measurements at ICU admission, 160 patients",
                       caption = "Synthetic data.")
finish(plot, "correlation_patients", "double")
