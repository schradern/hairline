two_series <- function() {
  data.frame(x = rep(1:3, 2), y = c(1, 2, 3, 2, 3, 4), group = rep(c("first", "second"), each = 3))
}

test_that("series colours follow slots and refuse too many categories", {
  hl_use(brand = FALSE)
  expect_equal(series_colors(c("Home", "Rehab")), c(Home = "#2474cf", Rehab = "#ef675a"))
  expect_error(series_colors(paste("group", 1:9)), "palette 'daylight' has 8 slots but 9 categories", fixed = TRUE)
})

test_that("light-slot lines are drawn 1.3 times heavier", {
  hl_use(brand = FALSE, palette = c("#2474cf", "#e8a628"))
  plot <- ggplot2::ggplot(two_series(), ggplot2::aes(x, y, colour = group)) + ggplot2::geom_line() + theme_hairline()
  data <- ggplot2::ggplot_build(plot)@data[[1]]
  widths <- tapply(data$linewidth, data$colour, unique)
  expect_equal(unname(widths["#e8a628"] / widths["#2474cf"]), 1.3)
})

test_that("point fills and density steps match the shared fixture", {
  cases <- read_fixture("points.json")
  for (case in cases$fills) expect_equal(point_fill(case$hex, case$surface), case$fill, info = case$hex)
  for (case in cases$steps) {
    expect_equal(point_step(case$count), c(radius = case$radius, opacity = case$opacity), info = case$count)
  }
})

test_that("points carry no outline and light slots get the darker fill", {
  hl_use(brand = FALSE, palette = c("#2474cf", "#e8a628"))
  plot <- ggplot2::ggplot(two_series(), ggplot2::aes(x, y, colour = group)) + ggplot2::geom_point() + theme_hairline()
  data <- ggplot2::ggplot_build(plot)@data[[1]]
  expect_true(all(data$shape == 16 & data$stroke == 0))
  expect_setequal(unique(data$colour), c("#2474cf", point_fill("#e8a628", "#ffffff")))
  expect_equal(unique(data$size), pt_to_mm(2 * 0.2 * 9 / 0.75))
  expect_equal(unique(data$alpha), 0.9)
})

test_that("dense points are smaller and more transparent per panel", {
  hl_use(brand = FALSE)
  dense <- data.frame(x = seq_len(2000), y = sin(seq_len(2000)))
  plot <- ggplot2::ggplot(dense, ggplot2::aes(x, y)) + ggplot2::geom_point() + theme_hairline()
  data <- ggplot2::ggplot_build(plot)@data[[1]]
  expect_equal(unique(data$size), pt_to_mm(2 * 0.1 * 9 / 0.75))
  expect_equal(unique(data$alpha), 0.5)
})

test_that("explicit point size and opacity are kept", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(two_series(), ggplot2::aes(x, y)) + ggplot2::geom_point(size = 3, alpha = 0.3) +
    theme_hairline()
  data <- ggplot2::ggplot_build(plot)@data[[1]]
  expect_equal(unique(data$size), 3)
  expect_equal(unique(data$alpha), 0.3)
})

test_that("point legend swatches show the darker fill", {
  hl_use(brand = FALSE, palette = c("#2474cf", "#e8a628"))
  plot <- ggplot2::ggplot(two_series(), ggplot2::aes(x, y, colour = group)) + ggplot2::geom_point() + theme_hairline()
  items <- legend_items(ggplot2::ggplot_build(plot))
  colours <- vapply(items, function(item) item$colour, character(1))
  expect_equal(unname(colours), c("#2474cf", point_fill("#e8a628", "#ffffff")))
})
