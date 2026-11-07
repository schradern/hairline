# One real day: which patient is where, then the doctors' tasks given to the first free doctor.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
stays <- gallery_data("unit_stays")
day <- stays[stays$day == "2026-01-07", ]
doctors <- day[day$section != "Recovery", ]
doctors$role <- "Doctors"
places <- hl_swimlanes(day, "place", "start", "end", label = "patient", group = "section")
tasks <- hl_swimlanes(doctors, NULL, "start", "end", label = "patient", group = "role", assign = "first_free",
                      color_by = "section")
plot <- hl_rows(places, tasks, heights = c(9, 3), sharex = TRUE, title = "One day in the unit",
                subtitle = "7 January 2026: places, then the doctors' tasks", caption = "Synthetic data.",
                height_mm = 150)
finish(plot, "swimlanes_day", "double")
