# Surface: the share of ICU beds occupied by hour of day across half a year, turned to show the midday ridge.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
hours <- gallery_data("hours")
plot <- hl_surface(hours, "hour", "week", "occupied", percent = TRUE, x_title = "Hour of day", y_title = "Week",
                   z_title = "Beds occupied", subtitle = "Share of beds in use, by hour of day and week",
                   caption = "Synthetic data. Read exact values from a heatmap beside it.")
finish(plot, "surface_hours", "double")
