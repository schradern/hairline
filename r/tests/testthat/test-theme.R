test_that("theme follows the frame rules", {
  hl_use(brand = FALSE)
  theme <- theme_hairline_elements(hl_settings())
  expect_equal(theme$plot.title.position, "plot")
  expect_equal(theme$plot.caption.position, "plot")
  expect_equal(theme$legend.position, "top")
  expect_equal(theme$legend.justification, "left")
  expect_equal(theme$legend.location, "plot")
  expect_equal(theme$panel.grid.major.y$colour, "#eef0f2")
  expect_s3_class(theme$axis.ticks.y, "ggplot2::element_blank")
  expect_s3_class(theme$panel.grid.major.x, "ggplot2::element_blank")
  expect_equal(theme$plot.title$size, 13.5)
  expect_equal(theme$plot.title$face, "bold")
  expect_equal(theme$strip.text$hjust, 0)
})

test_that("title size override reaches the theme", {
  hl_use(sizes = list(title = 14), brand = FALSE)
  expect_equal(theme_hairline_elements(hl_settings())$plot.title$size, 14)
})

test_that("discrete colour scale refuses more categories than slots", {
  hl_use(brand = FALSE)
  data <- data.frame(x = 1:9, y = 1:9, group = letters[1:9])
  plot <- ggplot2::ggplot(data, ggplot2::aes(x, y, colour = group)) + ggplot2::geom_point() +
    scale_colour_hairline()
  expect_error(ggplot2::ggplot_build(plot), "palette 'daylight' has 8 slots but 9 categories", fixed = TRUE)
})

test_that("axis tick labels carry no extra margin, so the plot starts where Python's does", {
  hl_use(brand = FALSE)
  theme <- theme_hairline_elements(hl_settings())
  expect_equal(as.numeric(theme$axis.text.y.left$margin), c(0, 0, 0, 0))
  expect_equal(as.numeric(theme$axis.text.x.bottom$margin), c(0, 0, 0, 0))
})

test_that("default point diameter is 2 x 0.2 x base size, as in Python", {
  hl_use(brand = FALSE)
  pointsize <- theme_hairline_elements(hl_settings())$geom$pointsize
  expect_equal(pointsize * ggplot2::.pt * 0.75, 2 * 0.2 * 9, tolerance = 1e-6)
})


test_that("supporting elements recede and the key number stands out", {
  hl_use(brand = FALSE)
  settings <- hl_settings()
  styles <- header_styles(settings)
  expect_equal(role_size(settings, "label"), 7.2)
  expect_equal(role_size(settings, "caption"), 7.2)
  expect_equal(styles$stat_label$colour, settings$neutral$faint)
  expect_equal(styles$stat_value$colour, settings$neutral$muted)
  expect_equal(styles$stat_value$weight, 400)
  expect_equal(styles$key_value$colour, settings$neutral$ink)
  expect_equal(styles$key_value$weight, 600)
})
