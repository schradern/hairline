# compare = and numbers =: differences with their CI and p beside the other numbers, the test named in the caption, and
# the numbers placed beside or under the rows (the Python package checks the same in test_comparisons.py).

compare_units <- function() {
  set.seed(1)
  data.frame(unit = rep(c("Unit A", "Unit B", "Unit C"), each = 40),
             days = round(stats::rlnorm(120, 2, 0.4) + rep(c(0, 1, 3), each = 40), 1))
}

test_that("Welch matches t.test and the shift its rank interval", {
  found <- welch_difference(c(1, 2, 3, 4, 5), c(2, 4, 6, 8, 10))
  test <- stats::t.test(c(1, 2, 3, 4, 5), c(2, 4, 6, 8, 10))
  expect_equal(c(found$low, found$high, found$p), c(test$conf.int, test$p.value))
  found <- shift_difference(c(4.1, 5.3, 6.0, 6.2, 7.7, 8.4, 9.1, 10.5), c(2.2, 3.1, 3.9, 4.4, 5.0, 5.8, 6.6))
  expect_equal(c(found$estimate, found$low, found$high, found$p), c(2.65, 0.3, 5.2, 0.0240277), tolerance = 1e-6)
})

test_that("compare names a group or adjacent", {
  expect_null(check_compare(NULL, "A", "spread"))
  expect_error(check_compare("all", c("A", "B"), "spread"), "would need a number for every pair")
  expect_error(check_compare("D", c("A", "B"), "spread"), "compare names 'D', which is not a group")
})

test_that("spread writes differences and names the test that follows the centre", {
  hl_use(brand = FALSE)
  spec <- spread_spec(compare_units(), "unit", "days", compare = "Unit A")
  expect_equal(vapply(spec$rows, function(row) row$pairs[[length(row$pairs) - 1]][2], ""),
               c("Reference", vapply(spec$rows[-1], function(row) row$pairs[[length(row$pairs) - 1]][2], "")))
  expect_match(spec$notes[length(spec$notes)], "^Δ: Hodges–Lehmann shift against Unit A")
  spec <- spread_spec(compare_units(), "unit", "days", compare = "adjacent", summary = c("mean", "ci"))
  expect_equal(spec$rows[[1]]$pairs[[length(spec$rows[[1]]$pairs)]], c("p", "–"))
  expect_match(spec$notes[length(spec$notes)], "Welch's t-test")
})

test_that("comparisons on raincloud, ridgeline and dot plot stay clear", {
  skip_if_not_installed("svglite")
  hl_use(brand = FALSE)
  rain <- hl_raincloud(compare_units(), "unit", "days", compare = "adjacent")
  expect_equal(vapply(rain@meta$hairline_table$rows, `[[`, "", "label"), c("", "Δ", "p"))
  expect_length(hl_check_layout(rain, size = "single"), 0)
  expect_length(hl_check_layout(hl_ridgeline(compare_units(), "unit", "days", compare = "Unit A", stats = "median"),
                                size = "onehalf"), 0)
  expect_length(hl_check_layout(hl_dotplot(compare_units(), "unit", "days", summary = c("mean", "ci"),
                                           compare = "Unit A"), size = "onehalf"), 0)
  expect_error(hl_dotplot(compare_units(), "unit", "days", compare = "Unit A"), "compare needs summary =")
  expect_error(hl_raincloud(cbind(compare_units(), site = "North"), "unit", "days", compare = "Unit A",
                            facet = "site"), "facet panels do not have")
})

test_that("numbers go beside or under the rows as asked", {
  skip_if_not_installed("svglite")
  hl_use(brand = FALSE)
  for (place in c("auto", "right", "below")) {
    plot <- hl_spread(compare_units(), "unit", "days", compare = "Unit A", stats = c("median", "n"), numbers = place)
    expect_length(hl_check_layout(plot, size = "onehalf"), 0)
  }
  expect_error(hl_spread(compare_units(), "unit", "days", numbers = "left"), "must be one of")
  crowded <- hl_spread(compare_units(), "unit", "days", compare = "Unit A", stats = c("median", "iqr", "mean", "n"),
                       numbers = "right")
  expect_error(hl_check_layout(crowded, size = "single"), "numbers beside the plot leave it.*use a wider size",
               class = "hairline_layout_error")
})
