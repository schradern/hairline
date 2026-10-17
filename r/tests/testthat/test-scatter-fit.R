test_that("correlation geometry and values match the shared fixture", {
  fixture <- read_fixture("correlation.json")
  measure <- function(text, role, weight = NULL) 0.5 * fixture$style$sizes[[role]] * nchar(text)
  for (case in fixture$cases) {
    hl_use(brand = FALSE)
    data <- as.data.frame(lapply(case$data, function(values) as.numeric(unlist(values))))
    spec <- correlation_spec(data, NULL, case$method)
    expected <- do.call(rbind, lapply(case$spec$matrix, function(row) as.numeric(unlist(row))))
    expect_equal(unname(spec$matrix), expected, tolerance = 1e-9)
    shapes <- correlation_drawing(spec, as.numeric(unlist(case$box)), measure, fixture$style)
    flat <- function(items) unlist(lapply(items, function(shape) {
      if (shape$kind == "text") c(shape$x, shape$y) else as.numeric(t(shape_points(shape)))
    }))
    expect_equal(flat(shapes), flat(case$shapes), tolerance = 1e-6)
    texts <- function(items) vapply(Filter(function(shape) shape$kind == "text", items), `[[`, character(1), "text")
    expect_equal(texts(shapes), texts(case$shapes))
    fills <- function(items) unlist(lapply(Filter(function(shape) shape$kind == "polygon", items), `[[`, "fill"))
    expect_equal(fills(shapes), fills(case$shapes))
  }
})

test_that("the scatter reports n, r and slope and draws the fit", {
  hl_use(brand = FALSE)
  set.seed(8)
  data <- data.frame(sofa = runif(90, 2, 14))
  data$lactate <- 0.6 + 0.3 * data$sofa + rnorm(90, 0, 0.8)
  plot <- hl_scatter(data, "sofa", "lactate")
  expect_equal(names(plot@meta$hairline_headers[[1]]$stats), c("n", "r", "Slope"))
  expect_equal(plot@labels$title, "Lactate and sofa")
  geoms <- vapply(plot@layers, function(layer) class(layer$geom)[1], character(1))
  expect_true(all(c("GeomRibbon", "GeomLine", "GeomPoint") %in% geoms))
})

test_that("the correlation heatmap has a colour key", {
  hl_use(brand = FALSE)
  set.seed(3)
  data <- data.frame(a = rnorm(30), b = rnorm(30), c = rnorm(30))
  report <- hl_layout_report(hl_correlation(data))
  expect_equal(report$legend_labels, c("−1", "−0.5", "0", "0.5", "1"))
  expect_error(hl_correlation(data.frame(a = 1:2, b = c("x", "y"))), "needs at least two numeric columns")
})
