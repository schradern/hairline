km_data <- function() {
  data.frame(arm = rep(c("A", "B"), each = 6), months = c(1, 2, 2, 3, 4, 5, 2, 4, 6, 8, 9, 12),
             died = c(1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0))
}

test_that("curves start at one and the median is in the header", {
  hl_use(brand = FALSE)
  plot <- hl_kaplan_meier(km_data(), "months", "died", by = "arm", title = "Survival",
                          stats = c(HR = "0.64 [0.45, 0.91]"))
  built <- ggplot2::ggplot_build(plot)
  steps <- built@data[[2]]
  expect_true(all(tapply(steps$y, steps$group, function(values) values[1]) == 1))
  header <- plot@meta$hairline_headers[[1]]
  expect_equal(names(header$stats), c("Median", "HR", "Log-rank"))
  expect_match(header$stats[["Median"]], " vs ")
})

test_that("number at risk aligns with the x ticks", {
  hl_use(brand = FALSE)
  report <- hl_layout_report(hl_kaplan_meier(km_data(), "months", "died", by = "arm", title = "Survival"))
  box <- report$plot_boxes[[1]]
  breaks <- nice_breaks(0, 12)
  expect_length(report$table_baselines, 3)
  expect_equal(report$table_value_xs[seq_along(breaks)], box[1] + breaks / max(breaks) * box[3], tolerance = 0.5)
})

test_that("a survfit object gives the same curves as raw data", {
  skip_if_not_installed("survival")
  hl_use(brand = FALSE)
  data <- km_data()
  fit <- survival::survfit(survival::Surv(months, died) ~ arm, data = data)
  raw <- ggplot2::ggplot_build(hl_kaplan_meier(data, "months", "died", by = "arm", title = "S"))@data[[2]]
  from_fit <- ggplot2::ggplot_build(hl_kaplan_meier(fit, title = "S"))@data[[2]]
  expect_equal(from_fit$y, raw$y)
})

test_that("a median that is not reached is named", {
  hl_use(brand = FALSE)
  plot <- hl_kaplan_meier(data.frame(months = 1:5, died = c(1, 0, 0, 0, 0)), "months", "died", title = "S")
  expect_equal(plot@meta$hairline_headers[[1]]$stats[["Median"]], "not reached")
})

test_that("groups keep their given order in the legend", {
  hl_use(brand = FALSE)
  plot <- hl_kaplan_meier(km_data(), "months", "died", by = "arm", order = c("B", "A"), title = "S")
  items <- legend_items(ggplot2::ggplot_build(plot))
  expect_equal(vapply(items, `[[`, character(1), "label"), c("B", "A"))
})

test_that("at-risk keys match the legend lines", {
  hl_use(brand = FALSE)
  plot <- hl_kaplan_meier(km_data(), "months", "died", by = "arm")
  parts <- frame_parts(ggplot2::ggplotGrob(plot)$table, ggplot2::ggplot_build(plot))
  expect_equal(table_keys(parts), c("line", "line"))
  spacing <- hl_tokens()$spacing
  expect_equal(table_label_offset(parts), (spacing$legend_swatch_line + spacing$legend_swatch_text) * 9)
})
