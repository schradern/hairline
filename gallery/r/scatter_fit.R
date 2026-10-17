# Scatter with a linear fit and its 95 % band; n, r and slope as key numbers.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_scatter(gallery_data("scatter"), "sofa", "lactate", by = "group", title = "Lactate rises with the SOFA score",
                   subtitle = "One dot per patient at admission", caption = "Synthetic data. Lactate in mmol/l.")
finish(plot, "scatter_fit", "double")
