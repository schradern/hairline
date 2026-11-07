# Facets as blocks of rows: occupied beds per unit, a block per year on one axis, the planned staffing level as a
# labelled reference and one unit highlighted, all options every chart shares.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
occupancy <- gallery_data("occupancy")
occupancy$occupied <- round(occupancy$share * occupancy$beds)
occupancy$year <- as.character(2025 + occupancy$day %/% 365)
plot <- hl_spread(occupancy, "ward", "occupied", facet = "year", highlight = "Unit B", reference = c(Planned = 10),
                  x_title = "Occupied beds at 00:00", stats = c("median", "iqr"), title = "Unit B stays above plan",
                  subtitle = "Occupied beds per day, 2025 and the first half of 2026", caption = "Synthetic data.")
finish(plot, "spread_years", "double")
