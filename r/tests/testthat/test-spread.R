spread_texts <- function(items) {
  vapply(Filter(function(shape) shape$kind == "text", items), `[[`, character(1), "text")
}
spread_numbers <- function(items) unlist(lapply(items, function(shape) {
  if (shape$kind == "text") c(shape$x, shape$y) else as.numeric(t(shape_points(shape)))
}))

test_that("spread specs and geometry match the shared fixture", {
  hl_use(brand = FALSE)
  fixture <- read_fixture("spread.json")
  box <- as.numeric(unlist(fixture$box))
  measure <- function(text, role, weight = NULL) 0.5 * fixture$style$sizes[[role]] * nchar(text)
  for (case in fixture$cases) {
    data <- as.data.frame(lapply(case$data, unlist), stringsAsFactors = FALSE)
    options <- case$options
    if (!is.null(options$marks)) options$marks <- unlist(options$marks)
    if (!is.null(options$stats)) options$stats <- unlist(options$stats)
    spec <- do.call(spread_spec, c(list(data = data, group = "group", value = case$value), options))
    expect_equal(vapply(spec$rows, `[[`, character(1), "text"),
                 vapply(case$spec$rows, `[[`, character(1), "text"))
    expect_equal(spec$axis$labels, unlist(case$spec$axis$labels))
    shapes <- spread_drawing(spec, box, measure, fixture$style)
    expect_equal(spread_texts(shapes), spread_texts(case$shapes))
    expect_equal(spread_numbers(shapes), spread_numbers(case$shapes), tolerance = 1e-6)
  }
})
