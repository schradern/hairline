cases <- function() read_fixture("statistics.json")
numbers <- function(values) as.numeric(unlist(values))

test_that("rank-sum, log-rank, fit and correlation match the shared fixture", {
  fixture <- cases()
  expect_equal(rank_sum_p(numbers(fixture$rank_sum$x), numbers(fixture$rank_sum$y)), fixture$rank_sum$p,
               tolerance = 1e-9)
  lr <- fixture$logrank
  result <- logrank_test(numbers(lr$time), numbers(lr$event), unlist(lr$group))
  expect_equal(result$chisq, lr$chisq, tolerance = 1e-9)
  expect_equal(result$p, lr$p, tolerance = 1e-9)
  fit <- linear_fit(numbers(fixture$fit$x), numbers(fixture$fit$y))
  for (key in c("slope", "intercept", "slope_se", "t")) expect_equal(fit[[key]], fixture$fit[[key]], tolerance = 1e-9)
  band <- fit_band(fit, c(0, 5, 10))
  expect_equal(c(band$centre, band$low, band$high), numbers(fixture$fit$band), tolerance = 1e-9)
  expect_equal(pearson_test(numbers(fixture$fit$x), numbers(fixture$fit$y)), numbers(fixture$pearson),
               tolerance = 1e-7)
  expect_equal(pearson_test(numbers(fixture$fit$x), numbers(fixture$fit$y), "spearman"), numbers(fixture$spearman),
               tolerance = 1e-7)
  expect_equal(egger_p(numbers(fixture$egger$estimate), numbers(fixture$egger$se)), fixture$egger$p, tolerance = 1e-9)
})

test_that("p values are formatted like the Python package", {
  for (case in cases()$format_p) expect_equal(format_p(case$value, case$locale), case$text)
})

test_that("the log-rank test matches survival::survdiff", {
  skip_if_not_installed("survival")
  lr <- cases()$logrank
  data <- data.frame(time = numbers(lr$time), event = numbers(lr$event), group = unlist(lr$group))
  expected <- survival::survdiff(survival::Surv(time, event) ~ group, data)
  expect_equal(logrank_test(data$time, data$event, data$group)$chisq, expected$chisq, tolerance = 1e-9)
})
