daylight <- function() unname(hl_tokens()$palettes$daylight)

ward_data <- function(wards) {
  data.frame(day = rep(1:3, length(wards)), share = seq_len(3 * length(wards)) / 10,
             ward = factor(rep(wards, each = 3), levels = wards))
}

built_colours <- function(plot) {
  data <- ggplot2::ggplot_build(plot)@data[[1]]
  vapply(split(data$colour, data$group), `[`, character(1), 1)
}

test_that("entity fixture cases match the Python reference", {
  for (case in read_fixture("entities.json")) {
    fixed <- unlist(case$fixed)
    requests <- as_colors(case$requests)
    if (!is.null(case$error)) {
      expect_error(assign_colors(as_colors(case$palette), case$label, fixed, requests), case$error, fixed = TRUE)
    } else {
      expect_equal(assign_colors(as_colors(case$palette), case$label, fixed, requests), unlist(case$expected))
    }
  }
})

test_that("automatic colours are stable across plots and reset by hl_use", {
  hl_use(brand = FALSE)
  expect_equal(hl_color("Unit A"), daylight()[1])
  expect_equal(hl_color("Unit D"), daylight()[2])
  expect_equal(hl_colors(), c("Unit A" = daylight()[1], "Unit D" = daylight()[2]))
  hl_use(brand = FALSE)
  expect_length(hl_colors(), 0)
})

test_that("a ward keeps its colour when a later plot shows other wards first", {
  hl_use(brand = FALSE)
  first <- ggplot2::ggplot(ward_data("Unit D"), ggplot2::aes(day, share, colour = ward)) + ggplot2::geom_line() +
    theme_hairline()
  built_colours(first)
  second <- ggplot2::ggplot(ward_data(c("Unit A", "Unit D")), ggplot2::aes(day, share, colour = ward)) +
    ggplot2::geom_line() + theme_hairline()
  expect_equal(unname(built_colours(second)), c(daylight()[2], daylight()[1]))
})

test_that("explicit and brand colours win, a user's manual scale stays", {
  hl_use(colors = c("Unit B" = daylight()[1]), brand = FALSE)
  plot <- ggplot2::ggplot(ward_data(c("Unit A", "Unit B")), ggplot2::aes(day, share, colour = ward)) +
    ggplot2::geom_line() + theme_hairline()
  expect_equal(unname(built_colours(plot)), c(daylight()[2], daylight()[1]))
  manual <- plot + ggplot2::scale_colour_manual(values = c("Unit A" = "#123456", "Unit B" = "#654321"))
  expect_equal(unname(built_colours(manual)), c("#123456", "#654321"))
  expect_error(hl_use(colors = c(x = "#12345"), brand = FALSE), "colors\\['x'\\]")
})

test_that("brand files map entities to palette names", {
  path <- file.path(withr::local_tempdir(), "_brand.yml")
  writeLines(c(readLines(testthat::test_path("fixtures", "example_brand.yml")), "    colors:",
               "      Unit B: poppy"), path)
  hl_use(brand = path)
  expect_equal(hl_color("Unit B"), hl_settings()$palette[2])
  expect_equal(hl_color("Unit A"), hl_settings()$palette[1])
  writeLines(c(readLines(testthat::test_path("fixtures", "example_brand.yml")), "    colors:",
               "      Unit B: lavender"), path)
  expect_error(hl_use(brand = path), "defaults.hairline.colors.Unit B: 'lavender' is not in color.palette")
  hl_use(brand = FALSE)
})
