budget <- function() {
  data.frame(source = c("Salary", "Salary", "Salary", "Salary", "Benefits", "Benefits", "Side job"),
             account = c("Joint", "Joint", "Savings", "Joint", "Joint", "Savings", "Joint"),
             category = c("Rent", "Food", "Reserve", "Leisure", "Food", "Reserve", "Leisure"),
             amount = c(1200, 450, 400, 250, 150, 100, 200))
}

as_numbers <- function(spec) {
  spec$nodes <- lapply(spec$nodes, function(nodes) lapply(nodes, function(node) {
    node$value <- as.numeric(node$value)
    node
  }))
  spec$links <- lapply(spec$links, function(link) {
    link$value <- as.numeric(link$value)
    link
  })
  spec$groups <- as.character(unlist(spec$groups))
  spec
}

test_that("sankey geometry matches the shared fixture", {
  fixture <- read_fixture("sankey.json")
  measure <- function(text, role, weight = NULL) 0.5 * fixture$style$sizes[[role]] * nchar(text)
  for (case in fixture$cases) {
    shapes <- sankey_drawing(as_numbers(case$spec), as.numeric(unlist(case$box)), measure, fixture$style)
    expect_equal(vapply(shapes, `[[`, character(1), "kind"), vapply(case$shapes, `[[`, character(1), "kind"))
    flat <- function(items) unlist(lapply(items, function(shape) {
      if (shape$kind == "text") c(shape$x, shape$y) else as.numeric(t(shape_points(shape)))
    }))
    expect_equal(flat(shapes), flat(case$shapes), tolerance = 1e-6)
    texts <- function(items) vapply(Filter(function(shape) shape$kind == "text", items), `[[`, character(1), "text")
    expect_equal(texts(shapes), texts(case$shapes))
  }
})

test_that("sankey specs match the shared fixture", {
  hl_use(brand = FALSE)
  fixture <- read_fixture("sankey.json")$cases[[1]]$spec
  spec <- sankey_spec(budget(), c("source", "account", "category"), "amount")
  expect_equal(vapply(spec$links, `[[`, character(1), "color"), vapply(fixture$links, `[[`, character(1), "color"))
  expect_equal(vapply(spec$nodes[[2]], `[[`, numeric(1), "value"),
               vapply(fixture$nodes[[2]], function(node) as.numeric(node$value), numeric(1)))
})

test_that("sankey inputs are checked", {
  data <- budget()
  data$amount[2] <- -5
  expect_error(sankey_spec(data, c("source", "account", "category"), "amount"),
               "Salary → Joint → Food has a negative value")
  expect_error(sankey_spec(budget(), "source", "amount"), "needs at least two columns")
})
