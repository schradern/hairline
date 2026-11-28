# Heatmap with marginal bars: bed occupancy by hour of day and week, each hour's and each week's mean beside the grid.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
hours <- gallery_data("hours")
plot <- hl_heatmap(hours, "hour", "week", "occupied", percent = TRUE, margins = "mean", x_title = "Hour of day",
                   y_title = "Week", z_title = "Beds occupied", title = "Beds fill up by midday",
                   subtitle = "Share of beds in use, by hour of day and week, with the mean of each",
                   caption = "Synthetic data.")
finish(plot, "heatmap_margins", "onehalf")
