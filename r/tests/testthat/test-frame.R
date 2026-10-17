occupancy <- function() {
  set.seed(3)
  data.frame(day = rep(1:120, 3), share = c(cumsum(rnorm(120, 0, 0.01)) + 0.6, cumsum(rnorm(120, 0, 0.01)) + 0.7,
                                            cumsum(rnorm(120, 0, 0.01)) + 0.8),
             ward = rep(c("Unit A", "Unit B", "Unit D"), each = 120))
}

test_that("faceted rows get one header line each and the panel gap", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(occupancy(), ggplot2::aes(day, share)) + ggplot2::geom_line() +
    ggplot2::facet_wrap(~ward, ncol = 1) + ggplot2::labs(title = "ICU bed occupancy", x = NULL, y = NULL) +
    theme_hairline() + hl_panel_header(panel = "Unit A", stats = c(Mean = "61.4%")) +
    hl_panel_header(panel = "Unit B") + hl_panel_header(panel = "Unit D")
  report <- hl_layout_report(plot, 174, 120)
  expect_length(report$panels, 3)
  expect_equal(report$panel_header_lines, c(1L, 1L, 1L))
  metrics <- font_metrics()
  upper <- report$panels[[1]]
  lower <- report$panels[[2]]
  header_top <- lower[2] - 0.6 * 9 - 9 * (metrics$cap_height + metrics$descender)
  expect_equal(header_top - (upper[2] + upper[4]), 2.25 * 9, tolerance = 0.02)
})

test_that("long titles wrap and stay inside the right margin", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(mtcars, ggplot2::aes(wt, mpg)) + ggplot2::geom_point() + theme_hairline() +
    ggplot2::labs(title = strrep("A very long title that keeps going ", 4))
  report <- hl_layout_report(plot, 85, 64)
  expect_gte(length(report$title_baselines), 2)
  expect_true(all(report$title_line_rights <= report$right + 0.5))
})

test_that("y title sits above the plot on the left edge and legend shares that edge", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(mtcars, ggplot2::aes(wt, mpg, colour = factor(cyl))) + ggplot2::geom_point() +
    ggplot2::labs(title = "Fuel use", y = "Miles per gallon", x = "Weight") + theme_hairline()
  report <- hl_layout_report(plot, 120, 84)
  expect_equal(report$y_title_left, 1.75 * 9)
  expect_lt(report$y_title_baseline, report$panels[[1]][2])
  expect_equal(report$legend_labels, c("4", "6", "8"))
  expect_length(report$legend_row_centers, 1)
})

test_that("panel header numbers that cannot fit are dropped with a warning", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(mtcars, ggplot2::aes(wt, mpg)) + ggplot2::geom_point() + ggplot2::labs(title = "T") +
    theme_hairline() + hl_panel_header("Name", stats = c(Alpha = strrep("1", 20), Beta = strrep("2", 20),
                                                         Gamma = strrep("3", 40)))
  path <- withr::local_tempfile(fileext = ".png")
  expect_warning(ggplot2::ggsave(path, plot, width = 85, height = 64, units = "mm", dpi = 72), "dropped.*Gamma")
})

test_that("default y scale uses nice breaks and locale labels", {
  hl_use(locale = "de", brand = FALSE)
  plot <- ggplot2::ggplot(data.frame(x = 0:2, y = c(0.21, 0.5, 0.88)), ggplot2::aes(x, y)) + ggplot2::geom_line() +
    theme_hairline()
  built <- ggplot2::ggplot_build(plot)
  scale <- built@layout$panel_scales_y[[1]]
  expect_equal(scale$get_breaks(), c(0, 0.25, 0.5, 0.75, 1.0))
  expect_equal(scale$get_labels()[1:2], c("0,00", "0,25"))
})

test_that("an explicit hairline scale without a target follows the panel-row rule", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(occupancy(), ggplot2::aes(day, share)) + ggplot2::geom_line() +
    ggplot2::facet_wrap(~ward, ncol = 1) + theme_hairline() + scale_y_hairline(percent = TRUE)
  expect_silent(built <- ggplot2::ggplot_build(plot))
  expect_length(stats::na.omit(built@layout$panel_scales_y[[1]]$get_breaks()), 3)
})

test_that("layout report applies the size preset's base size", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(mtcars, ggplot2::aes(wt, mpg)) + ggplot2::geom_point() + ggplot2::labs(title = "T") +
    theme_hairline()
  report <- hl_layout_report(plot, size = "single")
  expect_equal(report$left, 1.75 * 8)
})

test_that("x tick target follows the panel columns", {
  hl_use(brand = FALSE)
  data <- occupancy()
  data$copy <- rep(1:2, length.out = nrow(data))
  plot <- ggplot2::ggplot(data, ggplot2::aes(day, share)) + ggplot2::geom_line() +
    ggplot2::facet_wrap(~ward, ncol = 3) + theme_hairline()
  breaks <- stats::na.omit(ggplot2::ggplot_build(plot)@layout$panel_scales_x[[1]]$get_breaks())
  expect_length(breaks, 3)
})

test_that("edge tick labels align inward", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(data.frame(x = c(0, 10), y = c(0, 1)), ggplot2::aes(x, y)) + ggplot2::geom_line() +
    theme_hairline()
  find_text <- function(grob) {
    if (inherits(grob, "text")) return(grob)
    kids <- if (inherits(grob, "gtable")) grob$grobs else grob$children
    for (kid in kids) {
      found <- find_text(kid)
      if (!is.null(found)) return(found)
    }
    NULL
  }
  labels <- find_text(ggplot2::ggplotGrob(plot)$parts$panels[[1]]$axis_b)
  hjust <- rep_len(labels$hjust, length(labels$label))
  expect_equal(hjust[1], 0)
  expect_equal(hjust[length(hjust)], 1)
  expect_true(all(hjust[-c(1, length(hjust))] == 0.5))
})

test_that("trailing spaces count in measured widths", {
  hl_use(brand = FALSE)
  style <- role_style(hl_settings(), "label")
  expect_gt(text_width_pt("Estimate ", style), text_width_pt("Estimate", style) + 1)
})
