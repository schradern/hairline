stays <- function() {
  set.seed(6)
  data.frame(unit = rep(c("Surgical", "Medical", "Neuro", "Cardiac"), each = 50),
             length_of_stay = c(rgamma(50, 2, 0.5), rgamma(50, 3, 0.5), rgamma(50, 4, 0.5), rgamma(50, 5, 0.5)))
}

test_that("one ridge per group, the first on top, sharing one height scale", {
  hl_use(brand = FALSE)
  plot <- hl_ridgeline(stays(), length_of_stay ~ unit)
  built <- ggplot2::ggplot_build(plot)
  fills <- Filter(function(data) "fill" %in% names(data) && !all(data$fill == "#ffffff"), built@data)
  bases <- vapply(fills, function(data) min(data$y), numeric(1))
  expect_length(bases, 4)
  expect_equal(bases, c(3, 2, 1, 0))
  heights <- vapply(fills, function(data) max(data$y) - min(data$y), numeric(1))
  expect_equal(max(heights), 1.6, tolerance = 1e-6)
  expect_equal(plot@labels$title, "Length of stay by unit")
})

test_that("a group with one value draws no ridge", {
  hl_use(brand = FALSE)
  plot <- hl_ridgeline(data.frame(unit = c(rep("A", 5), "B"), days = c(1:5, 3)), "unit", "days")
  geoms <- vapply(plot@layers, function(layer) class(layer$geom)[1], character(1))
  expect_equal(sum(geoms == "GeomPath"), 1)
})
