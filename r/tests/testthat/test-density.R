test_that("density, bandwidth and quantiles match the shared fixture", {
  fixture <- read_fixture("density.json")
  for (case in fixture$cases) {
    values <- as.numeric(unlist(case$values))
    expect_equal(density_quantiles(values, c(0.25, 0.5, 0.75)), as.numeric(unlist(case$quantiles)), tolerance = 1e-9)
    curve <- density_curve(values)
    if (is.null(case$grid)) {
      expect_null(curve)
    } else {
      expect_equal(density_bandwidth(values), case$bandwidth, tolerance = 1e-9)
      expect_equal(curve$grid, as.numeric(unlist(case$grid)), tolerance = 1e-9)
      expect_equal(curve$height, as.numeric(unlist(case$height)), tolerance = 1e-9)
    }
  }
})

test_that("jitter and bracket levels match the shared fixture", {
  fixture <- read_fixture("density.json")
  expect_equal(jitter_offsets(12), as.numeric(unlist(fixture$jitter)), tolerance = 1e-12)
  for (case in fixture$brackets) {
    spans <- lapply(case$spans, function(span) as.numeric(unlist(span)))
    expect_equal(bracket_levels(spans), as.integer(unlist(case$levels)))
  }
})
