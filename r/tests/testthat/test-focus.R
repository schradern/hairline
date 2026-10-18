wards <- function() {
  set.seed(4)
  data.frame(day = rep(1:50, 3), share = c(runif(50, 0.4, 0.7), runif(50, 0.7, 0.98), runif(50, 0.6, 0.85)),
             ward = factor(rep(c("Unit A", "Unit B", "Unit D"), each = 50)))
}

STATS <- c(Mean = "87.0%", Median = "87.9%", "Days over 90%" = "42%")

test_that("the key number is emphasised", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(wards(), ggplot2::aes(day, share)) + ggplot2::geom_line() + ggplot2::labs(title = "T") +
    theme_hairline() + hl_panel_header("Unit B", stats = STATS, key = "Days over 90%")
  frame <- ggplot2::ggplotGrob(plot)
  composed <- compose_header(panel_header_for(frame$parts, 1), 20, 480, header_styles(hl_settings()),
                             header_gaps(hl_settings()))
  runs <- stats::setNames(composed$runs, vapply(composed$runs, `[[`, character(1), "text"))
  expect_equal(runs[["42%"]]$style$colour, hl_settings()$neutral$ink)
  expect_equal(runs[["42%"]]$style$weight, 600)
  expect_equal(runs[["87.0%"]]$style$colour, hl_settings()$neutral$muted)
  expect_error(hl_panel_header("x", stats = STATS, key = "Days"), "key 'Days' is not one of the key numbers")
})

test_that("highlighting a series keeps its colour and greys the rest", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(wards(), ggplot2::aes(day, share, colour = ward)) + ggplot2::geom_line() +
    theme_hairline() + hl_highlight(series = "Unit B")
  data <- ggplot2::ggplot_build(plot)@data[[1]]
  colours <- unique(data$colour)
  expect_setequal(colours, c("#de4642", "#b3b8be"))
  base <- pt_to_linewidth(0.14 * 9)
  expect_equal(unique(data$linewidth[data$colour == "#de4642"]), 1.15 * base, tolerance = 1e-6)
  expect_equal(unique(data$linewidth[data$colour == "#b3b8be"]), 0.85 * base, tolerance = 1e-6)
})

test_that("highlighting a panel by name greys the other panels without light-slot cues", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(wards(), ggplot2::aes(day, share)) + ggplot2::geom_point(colour = "#e8a628") +
    ggplot2::facet_wrap(~ward, ncol = 1) + theme_hairline() + hl_highlight(panels = "Unit B")
  data <- ggplot2::ggplot_build(plot)@data[[1]]
  context <- data[data$PANEL != 2, ]
  expect_true(all(context$fill == "#b3b8be"))
  expect_true(all(context$stroke == 0))
  expect_true(all(data$colour[data$PANEL == 2] == point_fill("#e8a628", "#ffffff")))
})

test_that("unknown highlights are named", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(wards(), ggplot2::aes(day, share, colour = ward)) + ggplot2::geom_line() +
    theme_hairline() + hl_highlight(series = "Pneumonia")
  expect_error(ggplot2::ggplot_build(plot), "highlight: 'Pneumonia' is not a series label; labels: Unit A")
})

test_that("reference lines sit behind the data with a label and legend entry", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(wards(), ggplot2::aes(day, share)) + ggplot2::geom_line() +
    ggplot2::facet_wrap(~ward, ncol = 1) + ggplot2::labs(title = "T") + theme_hairline() +
    hl_reference(y = 0.9, label = "90 %", legend_label = "High-load threshold")
  expect_s3_class(plot@layers[[1]]$geom, "GeomHline")
  frame <- ggplot2::ggplotGrob(plot)
  expect_equal(frame$parts$references[[1]]$label, "90 %")
  expect_equal(hl_layout_report(plot, size = "double")$legend_labels, "High-load threshold")
})

test_that("a reference label stays above its line unless it would reach the panel header", {
  hl_use(brand = FALSE)
  expect_false(reference_label_below(0.9, c(0, 1), panel_height = 50, label_size = 7.2, base_size = 9))
  expect_true(reference_label_below(1.0, c(0, 1), panel_height = 50, label_size = 7.2, base_size = 9))
})
