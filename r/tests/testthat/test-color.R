test_that("OKLCH round trip and known values", {
  for (color in c("#2474cf", "#e8a628", "#14325c", "#ffffff", "#000000", "#6f757d")) {
    expect_equal(do.call(oklch_to_hex, as.list(hex_to_oklch(color))), color)
  }
  expect_equal(round(hex_to_oklch("#14325c"), c(3, 3, 1)), c(0.319, 0.083, 257.4))
  expect_equal(round(contrast_ratio("#6f757d", "#ffffff"), 2), 4.65)
})

test_that("bad hex colours are named in the error", {
  expect_error(hex_to_oklab("#12345"), "'#12345' is not a 6-digit hex colour", fixed = TRUE)
})

test_that("colour fixture cases match the Python reference", {
  cases <- read_fixture("colour.json")
  for (case in cases$oklch) {
    expect_equal(hex_to_oklch(case$hex), unlist(case$oklch), tolerance = 1e-6)
  }
  for (case in cases$simulate) expect_equal(simulate_cvd(case$hex, case$kind), case$result)
  for (case in cases$delta_e) {
    expect_equal(delta_e(case$a, case$b, case$kind), case$value, tolerance = 1e-6)
  }
  for (case in cases$contrast) expect_equal(contrast_ratio(case$a, case$b), case$value, tolerance = 1e-6)
})
