occupancy_days <- function() {
  days <- seq(as.Date("2025-01-01"), by = "day", length.out = 60)
  do.call(rbind, lapply(list(c("Unit A", 0.6), c("Unit B", 0.88), c("Unit D", 0.78)), function(ward) {
    set.seed(nchar(ward[1]))
    data.frame(date = days, share = as.numeric(ward[2]) + stats::rnorm(60, 0, 0.05), ward = ward[1])
  }))
}

layer_geoms <- function(plot) vapply(plot@layers, function(layer) class(layer$geom)[1], character(1))

test_that("one panel per group with raw values under the rolling mean in entity colours", {
  hl_use(brand = FALSE)
  plot <- hl_timeseries(occupancy_days(), x = "date", y = "share", by = "ward", title = "ICU bed occupancy")
  built <- ggplot2::ggplot_build(plot)
  expect_equal(nrow(built@layout$layout), 3)
  lines <- which(layer_geoms(plot) == "GeomLine")
  raw <- built@data[[lines[1]]]
  mean <- built@data[[lines[2]]]
  expect_equal(unique(raw$alpha), 0.3)
  expect_equal(unique(raw$linewidth), 0.055 * 9 / ggplot2::.pt, tolerance = 1e-6)
  expect_equal(unique(mean$linewidth[mean$PANEL == 1]), 0.14 * 9 / ggplot2::.pt, tolerance = 1e-6)
  expect_equal(unique(mean$colour[mean$PANEL == 2]), hl_color("Unit B"))
  expect_equal(unique(raw$linewidth[raw$PANEL == 2]), 0.055 * 9 / ggplot2::.pt, tolerance = 1e-6)
})

test_that("the rolling mean is trailing with partial windows", {
  expect_equal(rolling_mean(c(1, 3, 5, 7, 9), 3), c(1, 2, 3, 5, 7))
})

test_that("key numbers, threshold and key emphasis", {
  hl_use(brand = FALSE)
  plot <- hl_timeseries(occupancy_days(), x = "date", y = "share", by = "ward", title = "T", percent = TRUE,
                        threshold = 0.9, threshold_label = "90 %", stats = c("mean", "median", "share_above"),
                        share_label = "Days over 90%", key = "share_above", key_panels = "Unit B")
  headers <- plot@meta$hairline_headers
  expect_equal(names(headers[["Unit B"]]$stats), c("Mean", "Median", "Days over 90%"))
  expect_equal(headers[["Unit B"]]$key, "Days over 90%")
  expect_null(headers[["Unit A"]]$key)
  expect_true("GeomHline" %in% layer_geoms(plot))
})

test_that("period mean, bands and events with a line-kind legend", {
  hl_use(brand = FALSE)
  plot <- hl_timeseries(occupancy_days(), x = "date", y = "share", by = "ward", title = "T", period_mean = TRUE,
                        bands = list(list(start = "2025-01-20", end = "2025-02-10", label = "Interim, reduced beds")),
                        events = list(list(x = "2025-01-20", label = "Move out")), raw_label = "Daily value",
                        mean_label = "7-day mean")
  report <- hl_layout_report(plot, size = "double")
  expect_equal(report$legend_labels, c("Daily value", "7-day mean", "Period mean", "Interim, reduced beds"))
  expect_true("GeomRect" %in% layer_geoms(plot))
  notes <- vapply(plot@meta$hairline_notes, `[[`, character(1), "label")
  expect_equal(notes, "Move out")
})

test_that("highlight greys the other panels and missing columns are named", {
  hl_use(brand = FALSE)
  plot <- hl_timeseries(occupancy_days(), x = "date", y = "share", by = "ward", title = "T", highlight = "Unit B")
  built <- ggplot2::ggplot_build(plot)
  mean <- built@data[[which(layer_geoms(plot) == "GeomLine")[2]]]
  expect_equal(unique(mean$colour[mean$PANEL == 1]), "#b3b8be")
  expect_error(hl_timeseries(occupancy_days(), x = "date", y = "occupancy", by = "ward", title = "T"),
               "column 'occupancy' is not in the data; columns: date, share, ward", fixed = TRUE)
})

test_that("bands and events can be limited to some panels", {
  hl_use(brand = FALSE)
  plot <- hl_timeseries(occupancy_days(), x = "date", y = "share", by = "ward", title = "T",
                        bands = list(list(start = "2025-01-20", end = "2025-02-10", label = "Interim",
                                          panels = c("Unit B", "Unit D"))),
                        events = list(list(x = "2025-01-20", label = "Move out", panels = "Unit D")))
  built <- ggplot2::ggplot_build(plot)
  rect <- built@data[[which(layer_geoms(plot) == "GeomRect")]]
  expect_setequal(as.integer(rect$PANEL), c(2L, 3L))
  vline <- built@data[[which(layer_geoms(plot) == "GeomVline")]]
  expect_equal(as.integer(vline$PANEL), 3L)
  expect_equal(plot@meta$hairline_notes[[1]]$panels, "Unit D")
})


test_that("highlight leaves bands and event lines alone, and date axes use month ticks", {
  hl_use(brand = FALSE)
  days <- seq(as.Date("2025-01-01"), as.Date("2026-06-30"), by = "day")
  data <- data.frame(date = rep(days, 2), share = 0.7, ward = rep(c("A", "B"), each = length(days)))
  plot <- hl_timeseries(data, x = "date", y = "share", by = "ward", title = "T", highlight = "B",
                        bands = list(list(start = "2025-05-01", end = "2026-05-01", label = "Interim")))
  built <- ggplot2::ggplot_build(plot)
  rect <- built@data[[which(layer_geoms(plot) == "GeomRect")]]
  expect_true(all(rect$fill == hl_settings()$neutral$band))
  scale <- built@layout$panel_scales_x[[1]]
  expect_equal(stats::na.omit(scale$get_labels()), c("2025", "May", "Sep", "2026", "May"), ignore_attr = TRUE)
})

test_that("event labels sit at the panel bottom", {
  hl_use(brand = FALSE)
  plot <- hl_timeseries(occupancy_days(), x = "date", y = "share", by = "ward", title = "T",
                        events = list(list(x = "2025-01-20", label = "Move out")))
  frame <- ggplot2::ggplotGrob(plot)
  plan <- plan_frame(frame$parts, c(493, 300))
  grob <- note_grobs(frame$parts, plan)[[1]]
  box <- plan$layout$panels[[1]]
  baseline_from_top <- 300 - grid::convertY(grob$y, "pt", valueOnly = TRUE)
  expect_lt(abs(baseline_from_top - (box[2] + box[4])), 4)
})
