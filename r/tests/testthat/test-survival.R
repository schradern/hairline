test_that("Kaplan-Meier estimates match the shared fixture", {
  for (case in read_fixture("survival.json")) {
    table <- km_estimate(unlist(case$time), unlist(case$event))
    for (column in c("time", "at_risk", "events", "censored", "survival", "low", "high")) {
      expected <- vapply(case$table[[column]], function(value) if (is.null(value)) NA_real_ else value, numeric(1))
      expect_equal(table[[column]], expected, tolerance = 1e-9, info = column)
    }
    expect_equal(km_median(table), case$median)
  }
})

test_that("Kaplan-Meier estimates match survival::survfit", {
  skip_if_not_installed("survival")
  case <- read_fixture("survival.json")[[7]]
  time <- unlist(case$time)
  event <- unlist(case$event)
  fit <- survival::survfit(survival::Surv(time, event) ~ 1)
  table <- km_estimate(time, event)
  expect_equal(table$survival, fit$surv, tolerance = 1e-9)
  expect_equal(table$low, fit$lower, tolerance = 1e-9)
  expect_equal(table$high, fit$upper, tolerance = 1e-9)
})

test_that("Kaplan-Meier inputs are checked", {
  expect_error(km_estimate(c(1, 2), c(1, 2)), "event values must be 0 or 1; found 2")
  expect_error(km_estimate(c(-1, 2), c(1, 1)), "time -1 is negative")
})

test_that("censor ticks are strokes of the token's length and width, not a glyph", {
  hl_use(brand = FALSE)
  data <- data.frame(months = c(2, 4, 5, 7, 9, 12), died = c(1, 0, 1, 0, 1, 0), arm = "A")
  plot <- hl_kaplan_meier(data, "months", "died", "arm")
  ticks <- Filter(function(layer) inherits(layer$geom, "GeomCensorTick"), plot@layers)
  expect_length(ticks, 1)
  rules <- hl_tokens()$survival
  base <- hl_settings()$base_size
  expect_equal(ticks[[1]]$geom_params$width_pt, rules$censor_width * base)
  expect_equal(ticks[[1]]$geom_params$length_pt, rules$censor_tick * base)
  expect_equal(nrow(ticks[[1]]$data), 3)
})
