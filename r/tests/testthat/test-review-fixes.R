cars <- function() {
  data <- mtcars
  data$cyl <- factor(data$cyl)
  data
}

framed_report <- function(plot, size = "onehalf") hl_layout_report(plot, size = size)

test_that("facet strips become panel headers without hl_panel_header()", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(cars(), ggplot2::aes(wt, mpg)) + ggplot2::geom_point() + ggplot2::facet_wrap(~cyl) +
    ggplot2::labs(title = "T") + theme_hairline()
  expect_equal(framed_report(plot)$panel_header_lines, c(1L, 1L, 1L))
})

test_that("an unfilled facet_wrap grid lays out the existing panels", {
  hl_use(brand = FALSE)
  data <- data.frame(x = rep(1:3, 5), y = runif(15), g = rep(letters[1:5], each = 3))
  plot <- ggplot2::ggplot(data, ggplot2::aes(x, y)) + ggplot2::geom_line() + ggplot2::facet_wrap(~g, ncol = 3) +
    ggplot2::labs(title = "T") + theme_hairline()
  report <- framed_report(plot, "double")
  expect_length(report$panels, 5)
})

test_that("coord_flip keeps axis titles with their axes", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(cars(), ggplot2::aes(wt, mpg)) + ggplot2::geom_point() + ggplot2::coord_flip() +
    ggplot2::labs(title = "T", x = "Weight", y = "Miles per gallon") + theme_hairline()
  parts <- ggplot2::ggplotGrob(plot)$parts
  expect_equal(parts$y_title, "Weight")
  expect_equal(parts$x_title, "Miles per gallon")
})

test_that("hairline plots keep their ggplot S3 classes for add-on packages", {
  plot <- ggplot2::ggplot(cars(), ggplot2::aes(wt, mpg)) + theme_hairline()
  expect_true(inherits(plot, "ggplot"))
  expect_true(inherits(plot, "gg"))
})

test_that("facet_grid panels take only their own axes", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(cars(), ggplot2::aes(wt, mpg)) + ggplot2::geom_point() + ggplot2::facet_grid(am ~ vs) +
    ggplot2::labs(title = "T") + theme_hairline()
  panels <- ggplot2::ggplotGrob(plot)$parts$panels
  has_axis <- function(grob) !inherits(grob, "zeroGrob")
  expect_equal(vapply(panels, function(panel) has_axis(panel$axis_l), logical(1)), c(TRUE, FALSE, TRUE, FALSE))
  expect_equal(vapply(panels, function(panel) has_axis(panel$axis_b), logical(1)), c(FALSE, FALSE, TRUE, TRUE))
})

test_that("columns with their own y labels get room", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(cars(), ggplot2::aes(wt, mpg)) + ggplot2::geom_point() +
    ggplot2::facet_wrap(~cyl, scales = "free_y") + ggplot2::labs(title = "T") + theme_hairline()
  report <- framed_report(plot, "double")
  first <- report$panels[[1]]
  second <- report$panels[[2]]
  expect_gt(second[1] - (first[1] + first[3]), 2 * 9 + 5)
})

test_that("legends hairline cannot draw are reported", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(cars(), ggplot2::aes(wt, mpg, colour = hp)) + ggplot2::geom_point() + theme_hairline()
  expect_warning(ggplot2::ggplotGrob(plot), "colour legend.*not supported")
})

test_that("a figure too small falls back with one warning instead of failing", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(cars(), ggplot2::aes(wt, mpg)) + ggplot2::geom_point() + ggplot2::facet_wrap(~cyl, ncol = 1) +
    ggplot2::labs(title = "T") + theme_hairline()
  path <- withr::local_tempfile(fileext = ".png")
  expect_warning(ggplot2::ggsave(path, plot, width = 60, height = 20, units = "mm", dpi = 72), "too small")
  expect_true(file.exists(path))
})

test_that("hl_save strips a known extension and leaves no partial file", {
  hl_use(brand = FALSE)
  folder <- withr::local_tempdir()
  plot <- ggplot2::ggplot(cars(), ggplot2::aes(wt, mpg)) + ggplot2::geom_point() + theme_hairline()
  path <- hl_save(plot, file.path(folder, "fig.png"), formats = "png", dpi = 72)
  expect_equal(basename(path), "fig.png")
  local_mocked_bindings(format_device = function(...) function() stop("disk full"))
  expect_error(hl_save(plot, file.path(folder, "broken"), formats = "png", dpi = 72), "disk full")
  expect_false(any(startsWith(list.files(folder, all.files = TRUE), "broken")))
})

test_that("a plot without layers draws an empty frame", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot() + ggplot2::labs(title = "Nothing yet") + theme_hairline()
  path <- withr::local_tempfile(fileext = ".png")
  expect_no_error(ggplot2::ggsave(path, plot, width = 100, height = 70, units = "mm", dpi = 72))
})

test_that("hairline plots compose with patchwork and cowplot", {
  skip_if_not_installed("patchwork")
  skip_if_not_installed("cowplot")
  hl_use(brand = FALSE)
  first <- ggplot2::ggplot(cars(), ggplot2::aes(wt, mpg)) + ggplot2::geom_point() + ggplot2::labs(title = "A") +
    theme_hairline()
  second <- ggplot2::ggplot(cars(), ggplot2::aes(hp, mpg)) + ggplot2::geom_point() + ggplot2::labs(title = "B") +
    theme_hairline()
  path <- withr::local_tempfile(fileext = ".png")
  combined <- patchwork::wrap_plots(first, second)
  expect_no_error(ggplot2::ggsave(path, combined, width = 170, height = 80, units = "mm", dpi = 72))
  cowplot::set_null_device("agg")
  expect_no_error(cowplot::plot_grid(first, second))
})

test_that("the frame draws the only x baseline", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(cars(), ggplot2::aes(wt, mpg)) + ggplot2::geom_point() + theme_hairline()
  expect_s3_class(ggplot2::ggplot_build(plot)@plot@theme$axis.line.x, "ggplot2::element_blank")
  expect_s3_class(theme_hairline_elements(hl_settings())$axis.line.x, "ggplot2::element_line")
})
