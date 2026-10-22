spread_texts <- function(items) {
  vapply(Filter(function(shape) shape$kind == "text", items), `[[`, character(1), "text")
}
spread_numbers <- function(items) unlist(lapply(items, function(shape) {
  if (shape$kind == "text") c(shape$x, shape$y) else as.numeric(t(shape_points(shape)))
}))

test_that("spread specs and geometry match the shared fixture", {
  hl_use(brand = FALSE)
  fixture <- read_fixture("spread.json")
  measure <- function(text, role, weight = NULL) 0.5 * fixture$style$sizes[[role]] * nchar(text)
  for (case in fixture$cases) {
    data <- as.data.frame(lapply(case$data, unlist), stringsAsFactors = FALSE)
    options <- case$options
    if (!is.null(options$marks)) options$marks <- unlist(options$marks)
    if (!is.null(options$stats)) options$stats <- unlist(options$stats)
    spec <- do.call(spread_spec, c(list(data = data, group = "group", value = case$value), options))
    expect_equal(lapply(spec$rows, function(row) lapply(row$pairs, as.list)),
                 lapply(case$spec$rows, `[[`, "pairs"))
    expect_equal(spec$axis$labels, unlist(case$spec$axis$labels))
    shapes <- spread_drawing(spec, as.numeric(unlist(case$box)), measure, fixture$style)
    expect_equal(spread_texts(shapes), spread_texts(case$shapes))
    expect_equal(spread_numbers(shapes), spread_numbers(case$shapes), tolerance = 1e-6)
  }
})

spread_style <- function() read_fixture("spread.json")$style
spread_measure <- function(text, role, weight = NULL) 0.5 * spread_style()$sizes[[role]] * nchar(text)

# Seven groups of response speeds, as in the demo paper that showed the collapse.
spread_nights <- function() {
  set.seed(3)
  data.frame(night = rep(paste("Night", 1:7), each = 40),
             speed = unlist(lapply(0:6, function(index) stats::rnorm(40, 3.2 - 0.12 * index, 0.4))))
}

spread_row_numbers <- function(shapes, name) {
  texts <- Filter(function(shape) shape$kind == "text" && is.null(shape$part), shapes)
  start <- which(vapply(texts, `[[`, character(1), "text") == name)
  texts[start + 1:6]
}

test_that("spread numbers sit beside the plot at a normal width", {
  hl_use(brand = FALSE)
  style <- spread_style()
  spec <- spread_spec(spread_nights(), "night", "speed", axis_title = "Response speed (1/s)")
  layout <- spread_layout(spec, c(20, 60, 440, 300), spread_measure, style, hl_tokens()$spread)
  expect_false(layout$under)
  expect_gte(layout$plot[2] - layout$plot[1], hl_tokens()$spread$min_plot * style$base)
  expect_gt(layout$lefts[1], layout$plot[2])
})

test_that("spread numbers move under each row when the plot would fall below its minimum", {
  hl_use(brand = FALSE)
  style <- spread_style()
  box <- c(20, 60, 240, 300)
  spec <- spread_spec(spread_nights(), "night", "speed", axis_title = "Response speed (1/s)")
  layout <- spread_layout(spec, box, spread_measure, style, hl_tokens()$spread)
  expect_true(layout$under)
  expect_equal(layout$plot[2], box[1] + box[3])
  expect_equal(layout$lefts[1], box[1])
  shapes <- spread_drawing(spec, box, spread_measure, style)
  name <- Find(function(shape) identical(shape$text, "Night 1"), shapes)
  row <- spread_row_numbers(shapes, "Night 1")
  expect_equal(vapply(row, `[[`, numeric(1), "y"), rep(name$y + line_height(style, "label"), 6))
  expect_equal(trimws(vapply(row[c(1, 3, 5)], `[[`, character(1), "text")), c("Median", "IQR", "Mean"))
  expect_lte(max(vapply(row, function(shape) shape$x + spread_measure(shape$text, "label"), numeric(1))),
             box[1] + box[3])
})

test_that("spread refuses a figure too narrow for the plot and its numbers, naming the room needed", {
  hl_use(brand = FALSE)
  spec <- spread_spec(spread_nights(), "night", "speed")
  expect_error(spread_drawing(spec, c(20, 60, 120, 300), spread_measure, spread_style()),
               "spread: the figure leaves 120 pt for the rows")
})

test_that("spread without numbers reaches the right edge with its plot", {
  hl_use(brand = FALSE)
  spec <- spread_spec(spread_nights(), "night", "speed", stats = character())
  layout <- spread_layout(spec, c(20, 60, 240, 300), spread_measure, spread_style(), hl_tokens()$spread)
  expect_equal(layout$plot[2], 260)
  expect_false(layout$under)
})
