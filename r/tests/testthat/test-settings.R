
test_that("the accent colours a lone series and the dark scheme swaps the neutrals", {
  settings <- hl_use(brand = FALSE, scheme = "dark", accent = "#2D1B69")
  expect_equal(settings$neutral, hl_tokens()$neutral_dark)
  expect_equal(settings$background, settings$neutral$surface)
  expect_equal(settings$accent, "#2d1b69")
  expect_false(identical(lone_colour(), "#2d1b69"))
  data <- data.frame(diagnosis = c("Sepsis", "Trauma", "Sepsis"))
  built <- ggplot2::ggplot_build(hl_bars(data, "diagnosis"))
  expect_equal(unique(built@data[[1]]$fill), lone_colour())
  expect_error(hl_use(brand = FALSE, scheme = "dim"), "scheme 'dim' must be 'light' or 'dark'")
  hl_use(brand = FALSE)
})
