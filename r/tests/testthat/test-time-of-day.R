stays <- function() {
  data.frame(place = c("Induction 1", "Theatre 1", "Theatre 2", "Theatre 1", "Recovery 1"),
             section = c("Induction", "Theatre", "Theatre", "Theatre", "Recovery"),
             patient = c("P1", "P1", "P2", "P3", "P1"),
             start = c("2026-01-05 07:20", "2026-01-05 07:40", "2026-01-05 09:00", "2026-01-06 08:00",
                       "2026-01-05 10:00"),
             end = c("2026-01-05 07:40", "2026-01-05 10:00", "2026-01-05 11:00", "2026-01-06 09:00",
                     "2026-01-05 11:30"))
}

staff <- function() {
  data.frame(role = rep(c("Doctors", "Nurses"), each = 3),
             start = rep(c("2026-01-05 08:00", "2026-01-05 09:00", "2026-01-06 08:30"), 2),
             end = rep(c("2026-01-05 12:00", "2026-01-05 10:00", "2026-01-06 11:00"), 2))
}

test_that("type 1 quantiles, first-free people and whole-number breaks follow the Python rules", {
  expect_equal(first_free(c(8, 8.5, 9, 10), c(9, 10, 9.5, 11)), c(1L, 2L, 1L, 1L))
  expect_equal(integer_breaks(-0.5, 6.5), c(0, 2, 4, 6))
  expect_equal(hour_breaks(6, 20, 7), c(6, 9, 12, 15, 18))
  expect_equal(hour_window(6.999999999999998, 18.75, 1), c(6, 20))
  expect_equal(clock_text(c(7.25, 25.5)), c("07:15", "01:30"))
  expect_equal(short_label("Theatre 2", "Theatre"), "2")
  expect_equal(step_index(0.6, c(0.25, 0.5, 0.75, 1)), 3)
})

test_that("the calendar filter keeps weekdays and names them with their n", {
  hl_use(brand = FALSE)
  origin <- as.POSIXct("2026-01-05", tz = "UTC")
  kept <- calendar(origin, 7, "weekdays", "lanes")
  expect_equal(kept$rows, 0:4)
  expect_equal(kept$label, "Weekdays, 5 days")
  expect_error(calendar(origin, 7, "holidays", "lanes"), "must be 'weekdays', 'weekends' or dates")
})

test_that("lanes draw rows in blocks, a binned key and a tooltip per cell", {
  hl_use(brand = FALSE)
  plot <- hl_lanes(stays(), "place", "start", "end", group = "section")
  expect_equal(vapply(plot@meta$hairline_blocks[[1]], `[[`, "", "name"), c("Induction", "Theatre", "Recovery"))
  expect_equal(plot@meta$hairline_ramp_key$labels, c("25%", "50%", "75%", "100%"))
  hover <- plot@meta$hairline_hover
  expect_equal(hover$text[1], "Induction 1, 07:15–07:30: 50%")
  report <- hl_layout_report(plot)
  expect_equal(report$legend_labels, c("Share of days", "25%", "50%", "75%", "100%"))
  expect_lt(utils::tail(report$legend_item_rights, 1), report$right - 100)
  expect_error(hl_lanes(stays(), "place", "start", "end", value = "mean"), "value 'mean' must be one of")
  expect_error(hl_lanes(stays(), "place", "start"), "give end =")
})

test_that("lanes name the calendar filter and draw the moves between rows", {
  hl_use(brand = FALSE)
  moves <- data.frame(from = "Induction 1", to = "Theatre 1", time = "2026-01-05 07:40")
  plot <- hl_lanes(stays(), "place", "start", "end", group = "section", days = "weekdays", flows = moves,
                   spans = list("Regular hours" = c(7, 16)))
  expect_equal(plot@labels$subtitle, "Weekdays, 2 days")
  expect_equal(vapply(plot@meta$hairline_legend, `[[`, "", "label"), c("Regular hours", "Move"))
  segments <- Filter(function(layer) inherits(layer$geom, "GeomSegment"), plot@layers)
  expect_length(segments, 1)
  bad <- data.frame(from = "Nowhere", to = "Theatre 1", time = "2026-01-05 07:40")
  expect_error(hl_lanes(stays(), "place", "start", "end", flows = bad), "flows name 'Nowhere'")
})

test_that("levels draw whole steps per group, the decision line named for tooltips", {
  hl_use(brand = FALSE)
  plot <- hl_levels(staff(), "start", end = "end", by = "role")
  headers <- plot@meta$hairline_headers
  # The typical day is the type 1 median of two daily peaks (2 and 1): the lower one.
  expect_equal(headers$Doctors$stats, c("Up to" = "2", Typical = "1"))
  steps <- Filter(function(layer) inherits(layer$geom, "GeomStep") && !isTRUE(layer$hairline_static), plot@layers)
  expect_equal(unname(vapply(steps, `[[`, "", "hairline_series")),
               c("Doctors: Enough on 90% of days", "Nurses: Enough on 90% of days"))
  expect_match(plot@labels$caption, "Quantiles on the data's own levels.", fixed = TRUE)
  expect_error(hl_levels(staff(), "start"), "give count =")
  expect_error(hl_levels(staff(), "start", end = "end", quantile = 1), "quantile must lie between 0 and 1")
})

test_that("swimlanes give tasks to the first free person and label bars where they fit", {
  hl_use(brand = FALSE)
  tasks <- data.frame(kind = "Doctors", patient = c("P1", "P2", "P3"), start = c(8, 8.5, 9.5), end = c(9, 10, 10))
  plot <- hl_swimlanes(tasks, NULL, "start", "end", label = "patient", group = "kind", assign = "first_free")
  expect_equal(plot@meta$hairline_hover$name, c("Doctors 1", "Doctors 2", "Doctors 1"))
  expect_equal(plot@meta$hairline_hover$text[1], "P1 · Doctors 1: 08:00–09:00")
  expect_length(plot@meta$hairline_inside, 3)
  expect_error(hl_swimlanes(tasks, NULL, "start", "end"), "give row =")
  expect_error(hl_swimlanes(tasks, "kind", "start", "end", assign = "random"), "assign 'random'")
})

test_that("rows share one time axis, sized by their heights, labelled at the bottom only", {
  hl_use(brand = FALSE)
  lanes <- hl_lanes(stays(), "place", "start", "end", group = "section")
  levels <- hl_levels(staff(), "start", end = "end", by = "role")
  plot <- hl_rows(lanes, levels, heights = c(6, 2, 4), title = "Cause above effect", caption = "Synthetic data.",
                  height_mm = 160)
  report <- hl_layout_report(plot, size = "double")
  heights <- vapply(report$panels, `[`, numeric(1), 4)
  expect_length(heights, 3)
  expect_equal(heights[1] / heights[2], 3, tolerance = 1e-3)
  expect_equal(heights[3] / heights[2], 2, tolerance = 1e-3)
  expect_equal(report$panel_header_lines, c(0L, 1L, 1L))
  expect_equal(plot@labels$caption, "Synthetic data. All days, 2 days. Quantiles on the data's own levels.")
  expect_true(all(c("Enough on 90% of days", "Share of days") %in% report$legend_labels))
  targets <- interactive_targets(plot, size = "double")
  names <- vapply(targets$series, `[[`, "", "name")
  expect_true(all(c("Theatre 1", "Doctors 1", "Doctors: Enough on 90% of days") %in% names))
  expect_error(hl_layout_report(hl_rows(lanes, levels, heights = c(1, 2)), size = "double"),
               "heights names 2 rows, but the plots make 3 panel rows")
  expect_error(hl_rows(lanes, 1), "plot 2 is not a hairline plot")
})

test_that("a figure too short for its smallest row names the height that fits", {
  hl_use(brand = FALSE)
  spec <- list(width_pt = 400, height_pt = 120, base_size = 9, panel_rows = 2, row_weights = c(20, 1),
               sizes = lapply(stats::setNames(nm = names(hl_tokens()$type$roles)), role_size, settings = hl_settings()))
  expect_error(compute_frame(spec, font_metrics()), "make it at least")
})

test_that("hl_legend_ramp draws outlined squares after the series items", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(data.frame(x = 1:2, y = 1:2, g = "Series"), ggplot2::aes(x, y, colour = g)) +
    ggplot2::geom_line() + ggplot2::labs(title = "Key") + theme_hairline() + hl_legend_ramp(title = "Share of days")
  report <- hl_layout_report(plot, size = "double")
  expect_equal(report$legend_labels, c("Series", "Share of days", "25%", "50%", "75%", "100%"))
  expect_lt(utils::tail(report$legend_item_rights, 1), report$right - 100)
  expect_error(hl_legend_ramp(steps = 2), "step 2 lies outside the limits")
  expect_error(hl_legend_ramp(format = "share"), "format 'share' must be")
})
