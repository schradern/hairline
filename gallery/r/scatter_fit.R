# Scatter with a linear fit and its 95 % band; n, r and slope as key numbers.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
patients <- gallery_data("scatter")
names(patients)[match(c("sofa", "lactate"), names(patients))] <- c("SOFA score", "Lactate (mmol/l)")
plot <- hl_scatter(patients, "SOFA score", "Lactate (mmol/l)", by = "group",
                   order = c("Low risk", "Medium risk", "High risk"), colors = "oranges",
                   title = "Lactate rises with the SOFA score", subtitle = "One dot per patient at admission",
                   caption = "Synthetic data.")
finish(plot, "scatter_fit", "double")
