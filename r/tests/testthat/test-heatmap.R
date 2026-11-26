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
                         gradient = case$gradient)
    expect_equal(fills(spec$fills), fills(case$spec$fills))
    expect_equal(unlist(spec$key$colors), unlist(case$spec$key$colors))
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
