# Heatmap: the share of ICU beds occupied by hour of day across half a year, one cell per hour and week, its colour
# blended along the ramp.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
hours <- gallery_data("hours")
plot <- hl_heatmap(hours, "hour", "week", "occupied", percent = TRUE, gradient = TRUE, x_title = "Hour of day",
                   y_title = "Week", z_title = "Beds occupied",
                   subtitle = "Share of beds in use, by hour of day and week", caption = "Synthetic data.")
finish(plot, "heatmap_hours", "onehalf")
