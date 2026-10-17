stays <- function() {
  data.frame(unit = rep(c("Surgical", "Medical", "Neuro"), c(6, 6, 4)),
             days = c(2, 3.5, 4, 5, 6.5, 9, 3, 5, 6, 7.5, 9, 12, 6, 9, 11, 15))
}

test_that("n labels sit under the groups", {
  hl_use(brand = FALSE)
  plot <- hl_raincloud(stays(), "unit", "days", title = "Length of stay")
  expect_equal(plot@meta$hairline_table$rows[[1]]$text, c("n = 6", "n = 6", "n = 4"))
  report <- hl_layout_report(plot)
  expect_length(report$table_value_xs, 3)
})

test_that("a single-value group draws no density", {
  hl_use(brand = FALSE)
  data <- data.frame(unit = c(rep("A", 5), "B"), days = c(1, 2, 3, 4, 5, 3))
  plot <- hl_raincloud(data, "unit", "days", title = "T")
  geoms <- vapply(plot@layers, function(layer) class(layer$geom)[1], character(1))
  expect_equal(sum(geoms == "GeomPolygon"), 1)
})

test_that("comparison names must be groups", {
  expect_error(hl_raincloud(stays(), "unit", "days", title = "T", comparisons = list(c("Surgical", "ICU", "p"))),
               "comparison group 'ICU' is not one of: Surgical, Medical, Neuro")
})
