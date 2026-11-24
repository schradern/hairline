# A drawn measure and two written ones per ward; one ward has no visitors recorded.
column_wards <- function(count = 40) {
  set.seed(4)
  data <- data.frame(ward = rep(c("North", "South", "East"), each = count),
                     stay = round(stats::rgamma(count * 3, 3, 0.5), 1), age = round(stats::rnorm(count * 3, 60, 12)),
                     visitors = as.numeric(stats::rpois(count * 3, 3)))
  data$visitors[data$ward == "East"] <- NA
  data
}

pair_labels <- function(row) vapply(row$pairs, `[`, "", 1)

test_that("written columns follow the stats, under a heading, and the caption names their statistics", {
  hl_use(brand = FALSE)
  spec <- spread_spec(column_wards(), "ward", "stay", stats = c("mean", "iqr", "n"), columns = c(age = "Age (years)"))
  expect_equal(pair_labels(spec$rows[[1]]), c("Mean", "IQR", "n", "Age (years)"))
  expect_equal(spec$headings, list(list(index = 4, label = "Age (years)")))
  expect_true("Age (years): Mean (IQR)." %in% spec$notes)
})

test_that("column names alone are labelled from their names; a group without values writes a dash", {
  hl_use(brand = FALSE)
  spec <- spread_spec(column_wards(), "ward", "stay", stats = "median", columns = c("age", "visitors"))
  expect_equal(vapply(spec$headings, `[[`, "", "label"), c("Age", "Visitors"))
  east <- Filter(function(row) row$name == "East", spec$rows)[[1]]
  expect_equal(east$pairs[[3]], c("Visitors", "–"))
})

test_that("a mark stays after the written columns so they line up", {
  hl_use(brand = FALSE)
  spec <- spread_spec(column_wards(), "ward", "stay", stats = "median", columns = "age", marks = c(North = 5),
                      mark_label = "Target")
  expect_equal(pair_labels(spec$rows[[1]]), c("Median", "Age", "Target"))
  expect_equal(pair_labels(spec$rows[[2]]), c("Median", "Age"))
})

test_that("written columns lay out cleanly, in facets too, and are numbers", {
  hl_use(brand = FALSE)
  data <- column_wards()
  data$year <- rep(c("2024", "2025"), 60)
  expect_length(hl_check_layout(hl_spread(data, "ward", "stay", facet = "year", columns = c(age = "Age")),
                                size = "double"), 0)
  expect_error(spread_spec(column_wards(), "ward", "stay", columns = "ward"), "'ward'")
  expect_error(spread_spec(column_wards(), "ward", "stay", columns = "weight"), "weight")
})

test_that("with written columns every number column is named once; without, rows keep their labels", {
  hl_use(brand = FALSE)
  headed <- spread_spec(column_wards(), "ward", "stay", stats = c("median", "n"), columns = c(age = "Age"))
  expect_equal(vapply(spread_every_heading(headed), `[[`, "", "label"), c("Median", "n", "Age"))
  plain <- spread_spec(column_wards(), "ward", "stay", stats = c("median", "n"))
  expect_length(spread_every_heading(plain), 0)
})
