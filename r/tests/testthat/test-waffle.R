test_that("waffle cells match the shared fixture", {
  fixture <- read_fixture("waffle.json")
  for (case in fixture$counts) {
    expect_equal(waffle_cell_counts(as.numeric(unlist(case$shares)), 100), as.numeric(unlist(case$cells)))
  }
})

test_that("waffle geometry matches the shared fixture", {
  fixture <- read_fixture("waffle.json")
  measure <- function(text, role, weight = NULL) 0.5 * fixture$style$sizes[[role]] * nchar(text)
  for (case in fixture$cases) {
    spec <- case$spec
    spec$ring <- lapply(spec$ring, function(segment) {
      segment$share <- as.numeric(segment$share)
      segment
    })
    shapes <- waffle_drawing(spec, as.numeric(unlist(case$box)), measure, fixture$style)
    expect_equal(vapply(shapes, `[[`, character(1), "kind"), vapply(case$shapes, `[[`, character(1), "kind"))
    flat <- function(items) unlist(lapply(items, function(shape) {
      if (shape$kind == "text") c(shape$x, shape$y) else as.numeric(t(shape_points(shape)))
    }))
    expect_equal(flat(shapes), flat(case$shapes), tolerance = 1e-6)
    texts <- function(items) vapply(Filter(function(shape) shape$kind == "text", items), `[[`, character(1), "text")
    expect_equal(texts(shapes), texts(case$shapes))
  }
})

test_that("waffle cells always add up to a hundred", {
  for (shares in list(c(0.004, 0.996), rep(1 / 7, 7), c(0.5049, 0.4951), rep(0.2, 5))) {
    expect_equal(sum(waffle_cell_counts(shares, 100)), 100)
  }
})

test_that("a waffle key too narrow names the waffle", {
  hl_use(brand = FALSE)
  discharge <- data.frame(destination = c("Home", "Rehab", "Ward", "Care home", "Died"),
                          patients = c(412, 168, 97, 54, 23))
  ring <- donut_rings(discharge, "destination", "patients", NULL)[[1]]
  style <- read_fixture("waffle.json")$style
  measure <- function(text, role, weight = NULL) 0.5 * style$sizes[[role]] * nchar(text)
  expect_error(waffle_drawing(list(ring = ring), c(0, 0, 60, 60), measure, style), "hairline: waffle: the key name")
})

test_that("a waffle needs values above zero", {
  hl_use(brand = FALSE)
  expect_error(hl_waffle(data.frame(a = c("x", "y"), n = c(0, 0)), "a", "n"), "hairline: waffle: no values above zero")
})
