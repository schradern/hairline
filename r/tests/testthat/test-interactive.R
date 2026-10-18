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
