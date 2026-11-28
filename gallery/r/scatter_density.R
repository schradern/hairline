# Scatter density: 2,400 admissions counted in hexagons, with the linear fit on top.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
vitals <- gallery_data("vitals")
names(vitals)[match(c("systolic", "diastolic"), names(vitals))] <- c("Systolic (mmHg)", "Diastolic (mmHg)")
plot <- hl_scatter(vitals, "Systolic (mmHg)", "Diastolic (mmHg)", density = TRUE,
                   title = "Diastolic pressure follows systolic pressure",
                   subtitle = "Blood pressure at ICU admission, counted in hexagons", caption = "Synthetic data.")
finish(plot, "scatter_density", "double")
