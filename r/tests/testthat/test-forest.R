forest_fixture <- function() read_fixture("forest.json")

numeric_spec <- function(spec) {
  for (field in c("null")) spec[[field]] <- as.numeric(spec[[field]])
  spec$axis$breaks <- as.numeric(unlist(spec$axis$breaks))
  spec$axis$labels <- as.character(unlist(spec$axis$labels))
  spec
}

test_that("log breaks match the shared fixture", {
  for (case in forest_fixture()$breaks) {
    expect_equal(log_breaks(case$low, case$high), as.numeric(unlist(case$breaks)), info = paste(case$low, case$high))
  }
})

test_that("forest geometry matches the shared fixture", {
  fixture <- forest_fixture()
  measure <- function(text, role, weight = NULL) 0.5 * fixture$style$sizes[[role]] * nchar(text)
  for (case in fixture$cases) {
    shapes <- forest_drawing(numeric_spec(case$spec), as.numeric(unlist(case$box)), measure, fixture$style)
    expect_equal(vapply(shapes, `[[`, character(1), "kind"), vapply(case$shapes, `[[`, character(1), "kind"))
    flat <- function(items) unlist(lapply(items, function(shape) {
      if (shape$kind == "text") c(shape$x, shape$y) else as.numeric(t(shape_points(shape)))
    }))
    expect_equal(flat(shapes), flat(case$shapes), tolerance = 1e-6)
    texts <- function(items) vapply(Filter(function(shape) shape$kind == "text", items), `[[`, character(1), "text")
    expect_equal(texts(shapes), texts(case$shapes))
  }
})

studies <- function() {
  data.frame(study = c("Adams 2019", "Baker 2020", "Chen 2021"), or = c(0.62, 0.81, 0.47), low = c(0.41, 0.55, 0.25),
             high = c(0.94, 1.19, 0.88), weight = c(31, 27, 12))
}

test_that("forest specs format texts and axis like the Python package", {
  hl_use(brand = FALSE)
  spec <- forest_spec(studies(), "study", "or", "low", "high", weight = "weight", colour = "#2474cf")
  expect_equal(spec$rows[[1]]$effect_text, "0.62 [0.41; 0.94]")
  expect_equal(spec$axis$labels, c("0.2", "0.5", "1", "2"))
})

test_that("a nonpositive limit on a ratio scale is named", {
  data <- studies()
  data$low[3] <- 0
  expect_error(forest_spec(data, "study", "or", "low", "high", colour = "#2474cf"),
               "'Chen 2021' has a limit of 0 or below on a ratio scale")
})

test_that("heterogeneity leads the caption", {
  hl_use(brand = FALSE)
  plot <- hl_forest(studies(), "study", "or", "low", "high", weight = "weight", title = "Mortality",
                    heterogeneity = "I2 = 18 %", caption = "Random effects.")
  expect_equal(plot@labels$caption, "I2 = 18 %. Random effects.")
  expect_equal(hl_layout_report(plot)$bare_panels, 0L)
})

test_that("a metafor fit is accepted", {
  skip_if_not_installed("metafor")
  fit <- metafor::rma(yi = log(c(0.62, 0.81, 0.47)), sei = c(0.21, 0.2, 0.32), measure = "OR",
                      slab = c("Adams", "Baker", "Chen"))
  plot <- hl_forest(fit, title = "Mortality")
  expect_match(plot@labels$caption, "tau")
})
