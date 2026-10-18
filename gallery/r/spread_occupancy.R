# Spread rows: occupied beds per unit at midnight, range, interquartile band and median, capacity as a tick.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
occupancy <- gallery_data("occupancy")
occupancy$occupied <- round(occupancy$share * occupancy$beds)
capacity <- tapply(occupancy$beds, occupancy$ward, function(values) values[1])
plot <- hl_spread(occupancy, "ward", "occupied", marks = capacity, mark_label = "beds", zero = TRUE,
                  axis_title = "Occupied beds at 00:00", title = "Occupied beds by unit",
                  subtitle = "Every day, January 2025 to June 2026; ticks mark the capacity", caption = "Synthetic data.")
finish(plot, "spread_occupancy", "double")
