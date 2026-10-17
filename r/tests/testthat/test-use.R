test_that("hl_use sets documented defaults", {
  settings <- hl_use(brand = FALSE)
  expect_equal(settings$base_size, 9)
  expect_equal(settings$palette_name, "daylight")
  expect_equal(settings$font, "Hairline Sans")
  expect_identical(hl_settings(), settings)
})

test_that("role sizes follow overrides and factors", {
  settings <- hl_use(base_size = 10, sizes = list(title = 14), brand = FALSE)
  expect_equal(role_size(settings, "title"), 14)
  expect_equal(role_size(settings, "label"), 8)
  expect_error(hl_use(sizes = list(heading = 12), brand = FALSE), "unknown text role 'heading'")
})

test_that("a missing font warns once and falls back", {
  expect_warning(settings <- hl_use(font = "Definitely Missing Sans", brand = FALSE), "is not installed")
  expect_equal(settings$font, "Hairline Sans")
  expect_no_warning(hl_use(font = "Definitely Missing Sans", brand = FALSE))
})

test_that("custom palettes and locale flow through", {
  hl_use(palette = c("#112233", "#445566"), locale = "de", brand = FALSE)
  expect_equal(hl_palette(), c("#112233", "#445566"))
  expect_equal(hl_format_percent(0.614), "61,4 %")
})
