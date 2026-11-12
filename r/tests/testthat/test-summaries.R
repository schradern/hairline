# summary = and stats =: one vocabulary of measures, drawn and written the same way on every distribution chart (the
# Python package checks the same in test_summaries.py).

summary_stays <- function(groups = 3, size = 30) {
  set.seed(7)
  names <- paste("Unit", LETTERS[seq_len(groups)])
  data.frame(unit = rep(names, each = size), days = round(stats::rlnorm(groups * size, 1.8, 0.4), 1))
}

legend_labels_of <- function(plot) vapply(plot@meta$hairline_legend %||% list(), `[[`, character(1), "label")

test_that("measures match their definitions", {
  found <- summary_values(1:10)
  expect_equal(c(found$median, found$q1, found$q3, found$mean), c(5.5, 3.25, 7.75, 5.5))
  expect_equal(found$sd, 3.0276504, tolerance = 1e-7)
  expect_equal(c(found$ci_low, found$ci_high), c(3.3341494, 7.6658506), tolerance = 1e-7)
  expect_true(is.nan(summary_values(4)$sd))
})

test_that("numbers are named in the locale", {
  hl_use(brand = FALSE)
  numbers <- list(function(value) sprintf("%.1f", value), function(value) sprintf("%.2f", value))
  pairs <- stat_pairs(1:10, c("median", "sd", "ci", "n"), numbers)
  expect_equal(pairs, list(c("Median", "5.5"), c("SD", "3.03"), c("95% CI", "3.33–7.67"), c("n", "10")))
  hl_use(brand = FALSE, locale = "de")
  on.exit(hl_use(brand = FALSE, locale = "en"))
  expect_equal(vapply(stat_pairs(c(1, 2), c("range", "ci"), numbers), `[`, "", 1), c("Spannweite", "95 %-KI"))
})

test_that("summaries are checked before drawing", {
  expect_error(check_summary(c("mean", "average"), "raincloud"), "unknown summary 'average'")
  expect_error(check_summary(c("median", "iqr", "ci"), "raincloud"), "'iqr' and 'ci' would draw two bars in one place")
  expect_error(check_summary(c("mean", "mean"), "spread"), "names 'mean' twice")
  expect_error(check_paired(c("median", "ci"), "dotplot"), "'ci' goes with the mean")
  expect_error(check_paired("iqr", "timeseries"), "needs one centre")
  expect_equal(check_paired(c("mean", "range"), "dotplot"), list(centre = "mean", interval = "range"))
})

test_that("raincloud draws the summary named in the legend and its numbers under the groups", {
  skip_if_not_installed("svglite")
  hl_use(brand = FALSE)
  plot <- hl_raincloud(summary_stays(), "unit", "days", summary = c("mean", "ci", "range"), stats = c("mean", "ci"))
  expect_equal(legend_labels_of(plot), c("Mean", "95% CI", "Range"))
  expect_equal(vapply(plot@meta$hairline_table$rows, `[[`, "", "label"), c("", "Mean", "95% CI"))
  expect_length(hl_check_layout(plot, size = "single"), 0)
  expect_length(legend_labels_of(hl_raincloud(summary_stays(), "unit", "days")), 0)
  expect_error(hl_raincloud(cbind(summary_stays(), site = "North"), "unit", "days", stats = "mean", facet = "site"),
               "use hl_spread\\(facet = ...\\)")
})

test_that("raincloud counts shorten before they meet; numbers that cannot stand apart stop the figure", {
  skip_if_not_installed("svglite")
  hl_use(brand = FALSE)
  expect_length(hl_check_layout(hl_raincloud(summary_stays(8, 20), "unit", "days"), size = "single"), 0)
  plot <- hl_raincloud(summary_stays(8, 20), "unit", "days", stats = c("iqr", "ci"))
  expect_error(hl_check_layout(plot, size = "single"), "do not fit side by side.*use a wider size",
               class = "hairline_layout_error")
})

test_that("spread draws a slim bar for the CI and writes SD and CI", {
  hl_use(brand = FALSE)
  spec <- spread_spec(summary_stays(), "unit", "days", summary = c("mean", "ci"), stats = c("mean", "sd", "ci"))
  row <- spec$rows[[1]]
  expect_true(row$bar$slim)
  expect_false(row$range)
  expect_false(row$show_median)
  expect_equal(vapply(row$pairs, `[`, "", 1), c("Mean", "SD", "95% CI"))
  expect_equal(vapply(spec$legend, `[[`, "", "label"), c("Mean", "95% CI"))
})

test_that("ridgeline marks centres and writes numbers beside each ridge", {
  skip_if_not_installed("svglite")
  hl_use(brand = FALSE)
  plot <- hl_ridgeline(summary_stays(4), "unit", "days", summary = c("median", "mean"), stats = c("median", "n"))
  expect_length(plot@meta$hairline_side_numbers[[1]], 8)
  expect_equal(legend_labels_of(plot), c("Median", "Mean"))
  expect_length(hl_check_layout(plot, size = "single"), 0)
  expect_error(hl_ridgeline(summary_stays(), "unit", "days", summary = c("median", "iqr")),
               "A ridge shows its own spread")
})

test_that("dotplot summarises rows per label", {
  skip_if_not_installed("svglite")
  hl_use(brand = FALSE)
  expect_length(hl_check_layout(hl_dotplot(summary_stays(), "unit", "days", summary = c("mean", "ci")),
                                size = "single"), 0)
  expect_error(hl_dotplot(cbind(summary_stays(), low = 1), "unit", "days", low = "low", high = "low",
                          summary = "mean"), "leave out")
  single <- data.frame(unit = c("A", "A", "B"), days = c(1, 2, 3))
  expect_error(hl_dotplot(single, "unit", "days", summary = c("mean", "sd")), "'B' has one value, and an SD needs")
})

test_that("timeseries summarises each x and names line and band", {
  skip_if_not_installed("svglite")
  hl_use(brand = FALSE)
  days <- seq(as.Date("2025-01-01"), by = "day", length.out = 20)
  data <- data.frame(day = rep(days, each = 5), score = (0:99) %% 17)
  plot <- hl_timeseries(data, "day", "score", summary = c("mean", "ci"), stats = c("mean", "sd", "n"))
  expect_equal(legend_labels_of(plot), c("Mean", "95% CI"))
  expect_length(hl_check_layout(plot, size = "single"), 0)
  expect_equal(unname(panel_stats(NA_real_, c("median", "n"), FALSE, NULL, "")), c("–", "–"))
})
