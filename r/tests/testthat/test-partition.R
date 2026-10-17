test_that("partition geometry matches the shared fixture", {
  fixture <- read_fixture("partition.json")
  measure <- function(text, role, weight = NULL) 0.5 * fixture$style$sizes[[role]] * nchar(text)
  for (case in fixture$cases) {
    spec <- case$spec
    spec$rings <- lapply(spec$rings, function(ring) lapply(ring, function(segment) {
      segment$share <- as.numeric(segment$share)
      segment
    }))
    shapes <- partition_drawing(spec, as.numeric(unlist(case$box)), measure, fixture$style)
    expect_equal(vapply(shapes, `[[`, character(1), "kind"), vapply(case$shapes, `[[`, character(1), "kind"))
    flat <- function(items) unlist(lapply(items, function(shape) {
      if (shape$kind == "text") c(shape$x, shape$y) else as.numeric(t(shape_points(shape)))
    }))
    expect_equal(flat(shapes), flat(case$shapes), tolerance = 1e-6)
    texts <- function(items) vapply(Filter(function(shape) shape$kind == "text", items), `[[`, character(1), "text")
    expect_equal(texts(shapes), texts(case$shapes))
  }
})

test_that("partition bars name the top level in the legend row", {
  hl_use(brand = FALSE)
  data <- data.frame(route = c("Home", "Home", "Rehab", "Other"), detail = c("Alone", "With support", "Inpatient", "Other"),
                     patients = c(250, 162, 120, 77))
  report <- hl_layout_report(hl_partition(data, c("route", "detail"), "patients", title = "Discharge",
                                          level_names = c("Destination", "Support")))
  expect_equal(report$legend_labels, c("Home", "Rehab", "Other"))
  expect_equal(report$bare_panels, 0L)
})

test_that("level names must match levels", {
  data <- data.frame(route = "Home", detail = "Alone", patients = 1)
  expect_error(hl_partition(data, c("route", "detail"), "patients", title = "T", level_names = "Destination"),
               "2 levels but 1 level name")
})
