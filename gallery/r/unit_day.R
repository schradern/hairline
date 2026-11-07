# Cause above effect on one time axis: the share of weekdays each place was occupied, the moves between places, and
# below, the doctors and nurses needed at once, as steps on whole people.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
hours <- list("Regular hours" = c(7, 16))
lanes <- hl_lanes(gallery_data("unit_stays"), "place", "start", "end", group = "section", days = "weekdays",
                  flows = gallery_data("unit_moves"), spans = hours)
staff <- hl_levels(gallery_data("unit_staff"), "start", end = "end", by = "role", days = "weekdays")
plot <- hl_rows(lanes, staff, heights = c(9, 3.5, 4.5), sharex = TRUE, title = "Occupancy and staffing over the day",
                subtitle = "Weekdays, January to July 2026", caption = "Synthetic data.", height_mm = 190)
finish(plot, "unit_day", "double")
