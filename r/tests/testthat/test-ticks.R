
test_that("month breaks and labels match the Python rule", {
  breaks <- month_breaks(as.Date("2025-01-01"), as.Date("2026-06-30"))
  expect_equal(breaks, as.Date(c("2025-01-01", "2025-05-01", "2025-09-01", "2026-01-01", "2026-05-01")))
  expect_equal(month_label(breaks[1:3], "en"), c("2025", "May", "Sep"))
  expect_equal(month_label(as.Date("2025-03-01"), "de"), "Mär")
  expect_equal(month_breaks(as.Date("2025-01-10"), as.Date("2025-03-20")), as.Date(c("2025-02-01", "2025-03-01")))
})
