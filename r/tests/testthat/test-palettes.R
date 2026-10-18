test_that("shipped palettes pass and daylight has the documented light slots", {
  for (name in c("daylight", "bloom", "citrus", "lagoon", "calm", "deep")) {
    report <- hl_check_palette(hl_palette(name))
    expect_true(report$passed, label = name)
    expect_gte(report$worst_cvd, 8)
  }
  expect_equal(hl_check_palette(hl_palette("daylight"))$light_slots, c(4L, 5L, 6L, 8L))
})

test_that("too many categories raise a named error", {
  expect_error(hl_palette("daylight", n = 9), "palette 'daylight' has 8 slots but 9 categories", fixed = TRUE)
  expect_error(hl_palette("sunset"), "unknown palette 'sunset'")
})

test_that("check and adapt fixtures match the Python reference", {
  cases <- read_fixture("checks.json")
  for (case in cases$checks) {
    report <- hl_check_palette(as_colors(case$colors), pairs = case$pairs)
    expect_equal(report$passed, case$passed)
    expect_equal(report$worst_cvd, case$worst_cvd, tolerance = 1e-6)
    expect_equal(report$worst_normal, case$worst_normal, tolerance = 1e-6)
    expect_equal(report$head_all_pairs, case$head_all_pairs, tolerance = 1e-6)
    expect_equal(report$light_slots, as.integer(unlist(case$light_slots)))
    expect_equal(length(report$failures), case$failures)
    expect_equal(length(report$warnings), case$warnings)
  }
  for (case in cases$adapt) expect_equal(adapt_readable(as_colors(case$colors)), as_colors(case$adapted))
  for (name in names(cases$ramps)) expect_equal(hl_ramp(name), as_colors(cases$ramps[[name]]))
  expect_length(hl_ramp("blues", n = 4), 4)
})

test_that("palette check messages name Delta E as Python does", {
  failures <- hl_check_palette(c("#2474cf", "#2b83c4", "#e8a628"), pairs = "all")$failures
  expect_equal(failures[3], "normal vision: worst ΔE 4.9 is below 15")
})
