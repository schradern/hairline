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
  texts <- c(unlist(lapply(built@data[-1], `[[`, "label")), vapply(plot@meta$hairline_inside, `[[`, "", "text"))
  expect_equal(sum(texts == "5"), 1)
  expect_equal(sum(texts == "3"), 2)
  expect_true(all(built@data[[1]]$colour == hl_settings()$neutral$surface))
})

test_that("stacked shares label percentages on a horizontal percent axis", {
  hl_use(brand = FALSE)
  plot <- hl_bars(outcomes(), "unit", by = "outcome", stacked = TRUE, percent = TRUE, horizontal = TRUE)
  expect_true("60%" %in% vapply(plot@meta$hairline_inside, `[[`, "", "text"))
  expect_length(ggplot2::ggplot_build(plot)@data, 1)
})

test_that("grouped bars name both columns in the default title", {
  data <- data.frame(unit = c("A", "A", "B"), sex = c("Female", "Male", "Female"))
  expect_equal(hl_bars(data, "unit", by = "sex")@labels$title, "Count by unit and sex")
})

side_by_side_shares <- function() {
  items <- c("Item A long name", paste("Item", LETTERS[2:8]))
  data.frame(item = rep(items, each = 3), unit = rep(c("Unit North", "Unit South", "Unit East"), length(items)),
             share = c(0.37, 0.39, 0.25, 0.31, 0.33, 0.36, 0.2, 0.4, 0.4, 0.13, 0.44, 0.43, 0.36, 0.38, 0.25, 0.3,
                       0.51, 0.19, 0.39, 0.39, 0.22, 0.25, 0.17, 0.57))
}

test_that("values beside horizontal bars side by side stand apart", {
  hl_use(brand = FALSE)
  plot <- hl_bars(side_by_side_shares(), "item", "share", by = "unit", percent = TRUE, horizontal = TRUE)
  expect_gt(plot@meta$hairline_min_plot, 0)
  overlaps <- Filter(function(finding) finding$rule == "text_overlap", hl_check_layout(plot))
  expect_length(overlaps, 0)
  lone <- side_by_side_shares()
  lone <- lone[lone$unit == "Unit North", ]
  expect_equal(hl_bars(lone, "item", "share", percent = TRUE, horizontal = TRUE)@meta$hairline_min_plot %||% 0, 0)
})
