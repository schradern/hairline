test_that("html export holds the svg, targets, script and font", {
  skip_if_not_installed("svglite")
  hl_use(brand = FALSE)
  data <- data.frame(x = rep(0:2, 2), y = c(1, 3, 2, 2, 1, 3), group = rep(c("North", "South"), each = 3))
  plot <- ggplot2::ggplot(data, ggplot2::aes(x, y, colour = group)) + ggplot2::geom_line() +
    ggplot2::labs(title = "Two series") + theme_hairline()
  path <- hl_save(plot, file.path(withr::local_tempdir(), "lines"), formats = "html")
  html <- paste(readLines(path, encoding = "UTF-8", warn = FALSE), collapse = "\n")
  expect_true(startsWith(html, "<!doctype html>") && grepl("<svg", html, fixed = TRUE) &&
                grepl("@font-face", html, fixed = TRUE))
  targets <- interactive_targets(plot)
  expect_equal(vapply(targets$series, `[[`, character(1), "name"), c("North", "South"))
  expect_equal(targets$series[[1]]$tips[[2]]$text, "North: 1, 3")
  expect_equal(vapply(targets$legend, `[[`, character(1), "name"), c("North", "South"))
})

test_that("fit lines stay static and points are targets", {
  hl_use(brand = FALSE)
  data <- data.frame(x = 1:6, y = c(1, 2.2, 2.9, 4.1, 5.2, 5.8))
  targets <- interactive_targets(hl_scatter(data, "x", "y", fit = "linear"))
  expect_length(targets$series, 1)
  expect_length(targets$series[[1]]$tips, 6)
})

test_that("the html figure is named by its title and subtitle", {
  skip_if_not_installed("svglite")
  hl_use(brand = FALSE)
  data <- data.frame(x = 0:2, y = c(1, 3, 2))
  plot <- ggplot2::ggplot(data, ggplot2::aes(x, y)) + ggplot2::geom_line() +
    ggplot2::labs(title = "Two series", subtitle = "Weekly <counts>") + theme_hairline()
  path <- hl_save(plot, file.path(withr::local_tempdir(), "named"), formats = "html")
  html <- paste(readLines(path, encoding = "UTF-8", warn = FALSE), collapse = "\n")
  expect_true(grepl('aria-label="Two series. Weekly &lt;counts>"', html, fixed = TRUE))
})

power_curve <- function(...) {
  hl_use(brand = FALSE)
  data <- data.frame(n = c(40, 80, 120, 160), power = c(0.05, 0.42, 0.896, 1))
  ggplot2::ggplot(data, ggplot2::aes(n, power)) + ggplot2::geom_line() +
    ggplot2::labs(title = "Power") + theme_hairline() + scale_y_hairline(percent = TRUE, ...)
}

tip_texts <- function(plot) vapply(interactive_targets(plot)$series[[1]]$tips, `[[`, character(1), "text")

test_that("scale digits reach the tooltips", {
  expect_equal(tip_texts(power_curve(digits = 1)), c("Power: 40, 5.0%", "Power: 80, 42.0%", "Power: 120, 89.6%",
                                                   "Power: 160, 100.0%"))
})

test_that("tooltip digits default to the shared rule", {
  expect_equal(tip_texts(power_curve())[3], "Power: 120, 90%")
})

test_that("scale digits leave the axis labels alone", {
  labels <- function(plot) ggplot2::ggplot_build(plot)@layout$panel_params[[1]]$y$get_labels()
  expect_equal(labels(power_curve(digits = 1)), labels(power_curve()))
})

test_that("scale digits apply to plain numbers on either axis", {
  hl_use(brand = FALSE)
  data <- data.frame(dose = c(0.5, 1.25, 2), response = c(1.5, 2.25, 3.125))
  plot <- ggplot2::ggplot(data, ggplot2::aes(dose, response)) + ggplot2::geom_line() +
    ggplot2::labs(title = "Response") + theme_hairline() + scale_y_hairline(digits = 2) +
    scale_x_hairline(digits = 0)
  expect_equal(tip_texts(plot), c("Response: 1, 1.50", "Response: 1, 2.25", "Response: 2, 3.13"))
})

test_that("scale digits must be a whole number from zero", {
  for (digits in list(-1, 1.5, "1", TRUE, NA_real_)) {
    expect_error(scale_y_hairline(digits = digits), "digits must be a whole number from 0 to 10")
  }
})
