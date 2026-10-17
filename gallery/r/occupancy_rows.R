# The ICU occupancy report: two levels of detail per ward, key numbers, threshold, interim period.
library(ggplot2)
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
occupancy <- gallery_data("occupancy")
occupancy$date <- as.Date("2025-01-01") + occupancy$day
wards <- c("Unit A", "Unit B", "Unit D")
beds <- tapply(occupancy$beds, occupancy$ward, max)
plot <- hl_timeseries(
  occupancy[occupancy$ward %in% wards, ], x = "date", y = "share", by = "ward", order = wards,
  title = "ICU bed occupancy", subtitle = "Share of beds occupied at 00:00 · 1 Jan 2025 – 30 Jun 2026",
  caption = "Threshold for high load: 90 %. Synthetic data.", percent = TRUE, threshold = 0.9, threshold_label = "90 %",
  threshold_legend = "High-load threshold", stats = c("mean", "median", "share_above"),
  share_label = "Days ≥ 90%", key = "share_above", key_panels = "Unit B", highlight = "Unit B",
  qualifiers = stats::setNames(lapply(wards, function(ward) paste(beds[[ward]], "beds")), wards),
  raw_label = "Daily value", mean_label = "7-day mean",
  bands = list(list(start = "2025-05-01", end = "2026-05-01", label = "Interim, reduced beds",
                    panels = c("Unit B", "Unit D"))),
  events = list(list(x = "2025-05-01", label = "Move out", panels = "Unit D"),
                list(x = "2026-05-01", label = "Move back", panels = "Unit D")))
finish(plot, "occupancy_rows", "double")
