surface_grid_data <- function(hours = 6:22, weeks = 1:8) {
  data <- expand.grid(hour = hours, week = weeks)
  data$share <- 0.5 + 0.3 * exp(-((data$hour - 12) / 3)^2) + 0.01 * data$week
  data
}

test_that("surface spec and shapes match the shared fixture", {
  fixture <- read_fixture("surface.json")
  measure <- function(text, role, weight = NULL) 0.5 * fixture$style$sizes[[role]] * nchar(text)
  flat <- function(items) unlist(lapply(items, function(shape) {
    if (shape$kind == "text") c(shape$x, shape$y) else as.numeric(t(shape_points(shape)))
  }))
  texts <- function(items) unlist(lapply(items, function(shape) shape$text %||% ""))
  fills <- function(rows) unlist(lapply(rows, function(row) vapply(row, function(fill) fill %||% "", "")))
  for (case in fixture$cases) {
    hl_use(brand = FALSE)
    data <- as.data.frame(lapply(case$data, function(values) {
      vapply(values, function(value) if (is.null(value)) NA_real_ else as.numeric(value), 0)
    }))
    spec <- surface_spec(data, "hour", "week", "load", case$titles, percent = case$percent,
                         gradient = isTRUE(case$gradient))
    expect_equal(unlist(spec$key$colors), unlist(case$spec$key$colors))
    expect_equal(spec$key$steps, as.numeric(unlist(case$spec$key$steps)), tolerance = 1e-9)
    expect_equal(fills(spec$fills), fills(case$spec$fills))
    expect_equal(unlist(spec$tips), unlist(case$spec$tips))
    expect_equal(unlist(lapply(spec$ticks$z, `[[`, "text")), unlist(lapply(case$spec$ticks$z, `[[`, "text")))
    shapes <- surface_scene_shapes(surface_scene(spec, measure, fixture$style), as.numeric(unlist(case$box)),
                                   case$view)
    expect_equal(flat(shapes), flat(case$shapes), tolerance = 1e-6)
    expect_equal(texts(shapes), texts(case$shapes))
  }
})

test_that("colour bins are half a tick step while the key keeps to one row", {
  expect_equal(grid_colour_steps(c(0.4, 0.6, 0.8), 0.87), c(0.5, 0.6, 0.7, 0.8, 0.9))
  expect_equal(grid_colour_steps(c(0.5, 0.6, 0.7, 0.8), 0.84), c(0.6, 0.7, 0.8, 0.9))
})

test_that("the surface keys its bins, lays out cleanly and turns in HTML", {
  hl_use(brand = FALSE)
  plot <- hl_surface(surface_grid_data(), "hour", "week", "share", percent = TRUE)
  expect_length(hl_check_layout(plot), 0)
  path <- tempfile(fileext = ".html")
  on.exit(unlink(path))
  skip_if_not_installed("svglite")
  hl_save(plot, sub("\\.html$", "", path), formats = "html")
  html <- paste(readLines(path, warn = FALSE), collapse = "\n")
  expect_match(html, "var hairlineSceneShapes", fixed = TRUE)
  expect_match(html, '"scenes":', fixed = TRUE)
})

test_that("the surface refuses data it cannot draw", {
  hl_use(brand = FALSE)
  data <- surface_grid_data()
  expect_error(hl_surface(rbind(data, data[1, ]), "hour", "week", "share"), "share an (hour, week) pair",
               fixed = TRUE)
  expect_error(hl_surface(surface_grid_data(hours = 8), "hour", "week", "share"), "'hour' needs 2 to 150",
               fixed = TRUE)
  empty <- transform(data, share = NA_real_)
  expect_error(hl_surface(empty, "hour", "week", "share"), "'share' is missing in every row", fixed = TRUE)
  sparse <- transform(data, share = ifelse((hour + week) %% 2 == 0, share, NA_real_))
  expect_error(hl_surface(sparse, "hour", "week", "share"), "no cell of the grid", fixed = TRUE)
  expect_error(hl_surface(data, "hour", "week", "share", elevation = 85), "elevation 85 must lie between 10 and 80",
               fixed = TRUE)
})
