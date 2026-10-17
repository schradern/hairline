# Grid of six panels, three columns, panel names only.
library(ggplot2)
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
occupancy <- gallery_data("occupancy")
occupancy$ward <- factor(occupancy$ward, levels = unique(occupancy$ward))
plot <- ggplot(occupancy, aes(day, mean7)) + geom_line(colour = hl_palette()[1]) + facet_wrap(~ward, ncol = 3) +
  labs(title = "Occupancy by unit", subtitle = "7-day mean, share of beds", caption = "Synthetic data.",
       x = NULL, y = NULL) +
  theme_hairline()
for (ward in levels(occupancy$ward)) plot <- plot + hl_panel_header(panel = ward)
finish(plot, "grid_panels", "double")
