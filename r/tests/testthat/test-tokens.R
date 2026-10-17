test_that("shared tokens load with every section", {
  tokens <- hl_tokens()
  expect_true(all(c("type", "spacing", "lines", "neutral", "palettes", "sets",
                    "ramps", "sizes", "locales", "checks", "font") %in% names(tokens)))
  expect_equal(tokens$spacing$panel_rows, 2.25)
  expect_equal(tokens$palettes$daylight[[1]], "#2474cf")
})
