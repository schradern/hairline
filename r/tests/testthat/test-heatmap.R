heatmap_fixture_frame <- function(case) {
  as.data.frame(lapply(case$data, function(values) {
    vapply(values, function(value) if (is.null(value)) NA_real_ else as.numeric(value), 0)
  }))
}

heatmap_flat_points <- function(items) unlist(lapply(items, function(shape) {
  if (shape$kind == "text") c(shape$x, shape$y) else as.numeric(t(shape_points(shape)))
}))

heatmap_grid_data <- function() {
  data <- expand.grid(hour = 6:22, week = 1:8)
  data$share <- 0.5 + 0.3 * exp(-((data$hour - 12) / 3)^2) + 0.01 * data$week
  data
}

test_that("heatmap spec and shapes match the shared fixture", {
  fixture <- read_fixture("heatmap.json")
  measure <- function(text, role, weight = NULL) 0.5 * fixture$style$sizes[[role]] * nchar(text)
  fills <- function(rows) unlist(lapply(rows, function(row) vapply(row, function(fill) fill %||% "", "")))
  tips <- function(items) unlist(lapply(items, function(shape) shape$tip %||% ""))
  for (case in fixture$cases) {
    hl_use(brand = FALSE)
    spec <- heatmap_spec(heatmap_fixture_frame(case), "hour", "week", "load", case$titles, percent = case$percent,
                         gradient = case$gradient, margins = case$margins)
    expect_equal(fills(spec$fills), fills(case$spec$fills))
    if (!is.null(case$margins)) {
      expected <- case$spec$margins
      known <- function(values) vapply(values, function(value) value %||% NA_real_, 0)
      expect_equal(spec$margins$columns, known(expected$columns), tolerance = 1e-9)
      expect_equal(spec$margins$rows, known(expected$rows), tolerance = 1e-9)
      expect_equal(spec$margins$texts$columns, unlist(expected$texts$columns))
      expect_equal(spec$margins$texts$rows, unlist(expected$texts$rows))
      expect_equal(spec$margins$word, expected$word)
    }
    expect_equal(unlist(spec$key$colors), unlist(case$spec$key$colors))
    expect_equal(spec$description, case$spec$description)
    layout <- heatmap_layout(heatmap_scene(spec, measure, fixture$style), as.numeric(unlist(case$box)),
                             height = case$height)
    expect_equal(heatmap_flat_points(layout$shapes), heatmap_flat_points(case$shapes), tolerance = 1e-6)
    expect_equal(tips(layout$shapes), tips(case$shapes))
    expect_equal(unlist(layout$cells), as.numeric(unlist(case$cells)), tolerance = 1e-6)
  }
})

test_that("surface and heatmap side by side match the shared fixture", {
  fixture <- read_fixture("heatmap.json")
  measure <- function(text, role, weight = NULL) 0.5 * fixture$style$sizes[[role]] * nchar(text)
  pair <- fixture$pair
  hl_use(brand = FALSE)
  spec <- surface_spec(heatmap_fixture_frame(pair), "hour", "week", "load", pair$titles, heatmap = TRUE)
  layout <- surface_pair_layout(surface_scene(spec, measure, fixture$style),
                                heatmap_scene(spec$flat, measure, fixture$style), as.numeric(unlist(pair$box)))
  expect_equal(heatmap_flat_points(layout$shapes), heatmap_flat_points(pair$shapes), tolerance = 1e-6)
  expect_equal(unlist(layout$cells), as.numeric(unlist(pair$cells)), tolerance = 1e-6)
})

test_that("the heatmap tags a series per row, lays out cleanly and pairs with the surface", {
  hl_use(brand = FALSE)
  plot <- hl_heatmap(heatmap_grid_data(), "hour", "week", "share", percent = TRUE)
  expect_length(hl_check_layout(plot), 0)
  series <- interactive_targets(plot)$series
  expect_equal(series[[1]]$name, "Week 1")
  pair <- hl_surface(heatmap_grid_data(), "hour", "week", "share", percent = TRUE, heatmap = TRUE)
  expect_equal(pair@meta$hairline_size, "double")
  expect_length(hl_check_layout(pair), 0)
  scene <- interactive_targets(pair)$scenes[[1]]
  expect_length(scene$flat$cells, 17 * 8)
  expect_error(hl_heatmap(transform(heatmap_grid_data(), share = NA_real_), "hour", "week", "share"),
               "'share' is missing in every row", fixed = TRUE)
})

test_that("marginal bars name their mean and light up with their row", {
  hl_use(brand = FALSE)
  plot <- hl_heatmap(heatmap_grid_data(), "hour", "week", "share", percent = TRUE, margins = "mean")
  expect_length(hl_check_layout(plot), 0)
  series <- interactive_targets(plot)$series
  names(series) <- vapply(series, `[[`, "", "name")
  expect_true(any(startsWith(vapply(series[["Week 1"]]$tips, `[[`, "", "text"), "Week 1: Mean ")))
  expect_true(startsWith(series[["Hour 12"]]$tips[[1]]$text, "Hour 12: Mean "))
})

test_that("marginal bars speak German and refuse what they cannot draw", {
  hl_use(brand = FALSE, locale = "de")
  on.exit(hl_use(brand = FALSE))
  spec <- heatmap_spec(heatmap_grid_data(), "hour", "week", "share", list(x = "Stunde", y = "Woche", z = "Anteil"),
                       margins = "sum")
  expect_equal(spec$margins$word, "Summe")
  expect_error(heatmap_spec(heatmap_grid_data(), "hour", "week", "share", list(x = "", y = "", z = ""),
                            margins = "median"), "must be 'mean', 'sum' or NULL")
  below <- heatmap_grid_data()
  below$share <- below$share - 1
  expect_error(heatmap_spec(below, "hour", "week", "share", list(x = "", y = "", z = ""), margins = "mean"),
               "bars from zero")
})
