# Arc diagram from raw rows: patient moves along a care pathway, counted per pair, width by count.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
stages <- c("Emergency", "Theatre", "ICU", "Step-down", "Ward", "Rehabilitation", "Home")
plot <- hl_arcs(gallery_data("pathways"), "origin", "destination", order = stages, title = "Moves along the care pathway",
                subtitle = "420 patient moves, 2025", caption = "Synthetic data.")
finish(plot, "arcs_pathways", "double")
