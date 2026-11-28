density_vitals <- function(count = 600) {
  set.seed(4)
  systolic <- stats::rnorm(count, 130, 18)
  data.frame(systolic = systolic, diastolic = 0.5 * systolic + stats::rnorm(count, 10, 6),
             unit = sample(c("North", "South", "East"), count, replace = TRUE))
}

test_that("hexagons match the shared fixture", {
  fixture <- read_fixture("hexagons.json")
  for (case in fixture$cases) {
    x <- as.numeric(unlist(case$x))
    y <- as.numeric(unlist(case$y))
    grid <- density_grid(x, y, case$bins, "scatter", as.numeric(unlist(case$shape)))
    expect_equal(unlist(grid), unlist(case$grid), tolerance = 1e-9)
    cells <- density_counts(x, y, grid)
    keys <- function(items) vapply(items, function(cell) paste(cell$row, cell$column, cell$count), "")
    expect_equal(keys(cells), keys(case$cells))
    centres <- function(items) unlist(lapply(items, function(cell) c(cell$x, cell$y)))
    expect_equal(centres(cells), centres(case$cells), tolerance = 1e-9)
    expect_equal(as.numeric(t(density_corners(cells[[1]], grid))), as.numeric(unlist(case$corners)),
                 tolerance = 1e-9)
  }
})

test_that("count bins match the shared fixture", {
  fixture <- read_fixture("hexagons.json")
  for (case in fixture$steps) expect_equal(density_steps(case$top), as.numeric(unlist(case$steps)))
})

test_that("density counts every point once and keeps the fit", {
  hl_use(brand = FALSE)
  data <- density_vitals()
  plot <- hl_scatter(data, "systolic", "diastolic", density = TRUE)
  tips <- unlist(lapply(plot@meta$hairline_targets, function(target) target$tips[[1]]$text))
  expect_equal(sum(as.numeric(sub(" .*", "", tips))), nrow(data))
  geoms <- vapply(plot@layers, function(layer) class(layer$geom)[1], "")
  expect_true("GeomPolygon" %in% geoms)
  expect_false("GeomPoint" %in% geoms)
  expect_true("GeomRibbon" %in% geoms)
  expect_match(plot@meta$hairline_description, "^Scatter plot with hexagonal bins\\. Linear fit: n = 600")
})

test_that("density facets share one lattice", {
  hl_use(brand = FALSE)
  plot <- hl_scatter(density_vitals(), "systolic", "diastolic", density = TRUE, facet = "unit", fit = NULL)
  hexagons <- Filter(function(layer) inherits(layer$geom, "GeomPolygon"), plot@layers)
  expect_length(hexagons, 3)
  widths <- unname(vapply(hexagons, function(layer) diff(range(layer$data$x[1:6])), 0))
  expect_equal(widths[1], widths[2])
})

test_that("density is German in a German figure", {
  hl_use(brand = FALSE, locale = "de")
  on.exit(hl_use(brand = FALSE))
  plot <- hl_scatter(density_vitals(), "systolic", "diastolic", density = TRUE, fit = NULL)
  tips <- unlist(lapply(plot@meta$hairline_targets, function(target) target$tips[[1]]$text))
  expect_true(all(grepl("Punkte?$", tips)))
})

test_that("density refuses what it cannot draw", {
  hl_use(brand = FALSE)
  data <- density_vitals()
  expect_error(hl_scatter(data, "systolic", "diastolic", by = "unit", density = TRUE), "takes no by =")
  expect_error(hl_scatter(data, "systolic", "diastolic", colors = c(North = "#000000"), density = TRUE),
               "colors must be a ramp name")
  expect_error(hl_scatter(data, "systolic", "diastolic", density = 1), "at least 2")
  expect_error(hl_scatter(data, "systolic", "diastolic", density = 2.5), "whole number")
  flat <- data.frame(x = c(1, 2, 3, 4), y = c(5, 5, 5, 5))
  expect_error(hl_scatter(flat, "x", "y", density = TRUE, fit = NULL), "spread along both axes")
})
