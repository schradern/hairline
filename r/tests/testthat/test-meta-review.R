meta_fixture <- function() read_fixture("meta_review.json")
fake <- function(style) function(text, role, weight = NULL) 0.5 * style$sizes[[role]] * nchar(text)
flat <- function(items) unlist(lapply(items, function(shape) {
  if (shape$kind == "text") c(shape$x, shape$y) else as.numeric(t(shape_points(shape)))
}))
texts <- function(items) vapply(Filter(function(shape) shape$kind == "text", items), `[[`, character(1), "text")

test_that("funnel specs and geometry match the shared fixture", {
  fixture <- meta_fixture()
  for (case in fixture$funnels) {
    hl_use(brand = FALSE)
    data <- as.data.frame(lapply(case$data, function(values) as.numeric(unlist(values))))
    spec <- funnel_spec(data, case$estimate, "se", case$ratio)
    expect_equal(spec$pooled, case$spec$pooled, tolerance = 1e-9)
    expect_equal(spec$egger, case$spec$egger, tolerance = 1e-9)
    expect_equal(spec$x_axis$labels, unlist(case$spec$x_axis$labels))
    shapes <- funnel_drawing(spec, as.numeric(unlist(fixture$box)), fake(fixture$style), fixture$style)
    expect_equal(flat(shapes), flat(case$shapes), tolerance = 1e-6)
    expect_equal(texts(shapes), texts(case$shapes))
  }
})

test_that("risk-of-bias specs and geometry match the shared fixture", {
  fixture <- meta_fixture()
  case <- fixture$risk_of_bias
  data <- as.data.frame(lapply(case$data, unlist), stringsAsFactors = FALSE, check.names = FALSE)
  spec <- risk_of_bias_spec(data, "study", domains = c("Randomisation", "Missing data", "Measurement"))
  expect_equal(lapply(spec$counts, as.numeric), lapply(case$spec$counts, function(row) as.numeric(unlist(row))))
  shapes <- risk_of_bias_drawing(spec, as.numeric(unlist(fixture$box)), fake(fixture$style), fixture$style)
  expect_equal(flat(shapes), flat(case$shapes), tolerance = 1e-6)
  expect_equal(texts(shapes), texts(case$shapes))
})

test_that("unknown judgements are named and the funnel reports Egger's test", {
  hl_use(brand = FALSE)
  wide <- data.frame(study = c("A", "B"), Randomisation = c("Low", "High"), Outcome = c("Maybe", "Low"))
  expect_error(risk_of_bias_spec(wide, "study", domains = c("Randomisation", "Outcome")),
               "judgement 'Maybe' for A, Outcome is not low, some concerns or high")
  trials <- data.frame(or = c(0.62, 0.81, 0.47, 1.05, 0.69), se = c(0.21, 0.19, 0.32, 0.2, 0.3))
  plot <- hl_funnel(trials, "or", "se", x_title = "Odds ratio")
  expect_match(plot@meta$hairline_headers[[1]]$stats[["Egger"]], "^p ")
  expect_equal(plot@labels$title, "Funnel plot of odds ratio")
})
