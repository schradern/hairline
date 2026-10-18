admissions <- function() {
  data.frame(diagnosis = rep(c("Sepsis", "Trauma", "Pneumonia", "Stroke"), c(6, 3, 8, 2)),
             sex = rep(c("f", "m"), 10)[1:19])
}

test_that("raw rows are counted and sorted by value", {
  hl_use(brand = FALSE)
  plot <- hl_bars(admissions(), "diagnosis")
  data <- ggplot2::ggplot_build(plot)@data[[1]]
  expect_equal(data$y[order(data$x)], c(8, 6, 3, 2))
  expect_equal(levels(plot@layers[[1]]$data$category), c("Pneumonia", "Sepsis", "Trauma", "Stroke"))
  expect_equal(plot@labels$title, "Count by diagnosis")
})

test_that("groups get a legend and long labels turn the bars horizontal", {
  hl_use(brand = FALSE)
  report <- hl_layout_report(hl_bars(admissions(), "diagnosis", by = "sex"))
  expect_equal(report$legend_labels, c("f", "m"))
  data <- data.frame(reason = c("Respiratory failure after surgery", "Sepsis", "Sepsis"))
  built <- ggplot2::ggplot_build(hl_bars(data, "reason"))@data[[1]]
  expect_true(all(built$flipped_aes))
})

test_that("stacked shares reach one hundred percent", {
  hl_use(brand = FALSE)
  built <- ggplot2::ggplot_build(hl_bars(admissions(), "diagnosis", by = "sex", stacked = TRUE, percent = TRUE))
  tops <- tapply(built@data[[1]]$ymax, built@data[[1]]$x, max)
  expect_true(all(abs(tops - 1) < 1e-9))
})

test_that("the dot plot sorts by value and draws dots", {
  hl_use(brand = FALSE)
  units <- data.frame(unit = c("A", "B", "C", "D"), mortality = c(0.12, 0.21, 0.08, 0.15))
  plot <- hl_dotplot(units, "unit", "mortality")
  shapes <- plot@meta$hairline_drawing(c(0, 0, 400, 160), measure_for(hl_settings()), drawing_style(hl_settings()))
  rows <- vapply(Filter(function(shape) shape$kind == "text" && shape$text %in% c("A", "B", "C", "D"), shapes),
                 `[[`, character(1), "text")
  expect_equal(rows, c("B", "D", "A", "C"))
  expect_equal(sum(vapply(shapes, function(shape) identical(shape$role, "dot"), logical(1))), 4)
})

outcomes <- function() {
  data.frame(unit = rep(c("Medical", "Surgical", "Neuro"), c(5, 4, 3)),
             outcome = c("Home", "Home", "Home", "Ward", "Died", "Home", "Home", "Ward", "Ward", "Home", "Ward", "Died"))
}

test_that("stacked segments carry their values, bars their totals, segments are separated", {
  hl_use(brand = FALSE)
  plot <- hl_bars(outcomes(), "unit", by = "outcome", stacked = TRUE, sort = "given")
  built <- ggplot2::ggplot_build(plot)
  texts <- unlist(lapply(built@data[-1], `[[`, "label"))
  expect_equal(sum(texts == "5"), 1)
  expect_equal(sum(texts == "3"), 2)
  expect_true(all(built@data[[1]]$colour == hl_settings()$neutral$surface))
})

test_that("stacked shares label percentages on a horizontal percent axis", {
  hl_use(brand = FALSE)
  plot <- hl_bars(outcomes(), "unit", by = "outcome", stacked = TRUE, percent = TRUE, horizontal = TRUE)
  texts <- unlist(lapply(ggplot2::ggplot_build(plot)@data[-1], `[[`, "label"))
  expect_true("60%" %in% texts)
  expect_length(ggplot2::ggplot_build(plot)@data, 2)
})
