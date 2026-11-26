# Surface beside its heatmap: the share of ICU beds occupied by hour of day across half a year; the surface shows
# the midday ridge, the heatmap the values, and in HTML a point marked in one is marked in the other.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
hours <- gallery_data("hours")
plot <- hl_surface(hours, "hour", "week", "occupied", percent = TRUE, heatmap = TRUE, x_title = "Hour of day",
                   y_title = "Week", z_title = "Beds occupied",
                   subtitle = "Share of beds in use, by hour of day and week", caption = "Synthetic data.")
finish(plot, "surface_hours", "double")
