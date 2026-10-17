flows_fixture <- function() read_fixture("flows.json")
fake_width <- function(style) function(text, role, weight = NULL) 0.5 * style$sizes[[role]] * nchar(text)
flat_shapes <- function(items) unlist(lapply(items, function(shape) {
  if (shape$kind == "text") c(shape$x, shape$y) else as.numeric(t(shape_points(shape)))
}))
shape_texts <- function(items) vapply(Filter(function(shape) shape$kind == "text", items), `[[`, character(1), "text")

test_that("PRISMA geometry matches the shared fixture", {
  hl_use(brand = FALSE)
  fixture <- flows_fixture()
  counts <- fixture$prisma$counts
  counts$excluded_reasons <- unlist(counts$excluded_reasons)
  spec <- prisma_spec(counts)
  shapes <- prisma_drawing(spec, as.numeric(unlist(fixture$box)), fake_width(fixture$style), fixture$style)
  expect_equal(shape_texts(shapes), shape_texts(fixture$prisma$shapes))
  expect_equal(flat_shapes(shapes), flat_shapes(fixture$prisma$shapes), tolerance = 1e-6)
})

test_that("arc geometry matches the shared fixture, crowded labels included", {
  hl_use(brand = FALSE)
  fixture <- flows_fixture()
  for (case in fixture$arcs) {
    data <- as.data.frame(lapply(case$data, unlist), stringsAsFactors = FALSE)
    spec <- arcs_spec(data, "origin", "destination")
    shapes <- arcs_drawing(spec, as.numeric(unlist(fixture$box)), fake_width(fixture$style), fixture$style)
    expect_equal(shape_texts(shapes), shape_texts(case$shapes))
    expect_equal(flat_shapes(shapes), flat_shapes(case$shapes), tolerance = 1e-6)
    expect_equal(vapply(shapes, function(shape) shape$rotation %||% 0, numeric(1)),
                 vapply(case$shapes, function(shape) as.numeric(shape$rotation %||% 0), numeric(1)))
  }
})

test_that("PRISMA counts that do not add up give a warning", {
  hl_use(brand = FALSE)
  counts <- list(identified = 1240, duplicates = 260, screened = 970, included = 18)
  expect_warning(prisma_spec(counts), "screened 970 is not identified 1,240 minus removed 260")
  expect_error(prisma_spec(list(identified = 10)), "needs identified, screened and included")
})

test_that("drawn charts fit the figure height to their content", {
  hl_use(brand = FALSE)
  plot <- hl_dotplot(data.frame(unit = c("A", "B", "C"), rate = c(0.1, 0.2, 0.15)), "unit", "rate")
  fitted <- fitted_size_mm(plot, figure_size_mm("double", NULL, NULL))
  expect_lt(fitted[2], figure_size_mm("double", NULL, NULL)[2])
  report <- hl_layout_report(plot, size = "double")
  box <- report$plot_boxes[[1]]
  texts <- report$drawing_texts
  expect_lt(abs(box[2] + box[4] - max(vapply(texts, `[`, numeric(1), 2))), 15)
})
