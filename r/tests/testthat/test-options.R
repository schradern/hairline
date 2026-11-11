patients <- function() {
  set.seed(4)
  data.frame(group = rep(c("Low", "Mid", "High"), each = 30), site = rep(c("North", "South"), 45),
             sofa = stats::runif(90, 1, 14), lactate = stats::runif(90, 0.5, 6))
}

drawn_texts <- function(plot) {
  shapes <- plot@meta$hairline_drawing(c(0, 0, 600, 400), measure_for(hl_settings()), drawing_style(hl_settings()))
  unlist(lapply(shapes, `[[`, "text"))
}

test_that("references take a value, several or a named vector", {
  expect_equal(option_references(0.9, "bars"), list(list(value = 0.9, label = NULL)))
  expect_equal(option_references(c(Target = 2), "bars"), list(list(value = 2, label = "Target")))
  expect_length(option_references(c(1, 2), "bars"), 2)
  expect_error(option_references("x", "bars"), "reference must be finite numbers")
})

test_that("groups sort by median, mean or n and keep ties in order", {
  groups <- list(a = c(1, 2), b = c(5, 6, 7), c = c(5, 6, 7))
  expect_equal(sorted_names(names(groups), function(name) groups[[name]], "median", "x"), c("b", "c", "a"))
  expect_equal(sorted_names(names(groups), function(name) groups[[name]], "n", "x"), c("b", "c", "a"))
  expect_equal(sorted_names(names(groups), function(name) groups[[name]], NULL, "x"), c("a", "b", "c"))
  expect_error(sorted_names(names(groups), function(name) groups[[name]], "size", "x"), "sort 'size' must be one of")
})

test_that("every chart with a legend takes a key title", {
  hl_use(brand = FALSE)
  data <- patients()
  for (plot in list(hl_scatter(data, "sofa", "lactate", by = "group", key_title = "Risk"),
                    hl_bars(data, "site", by = "group", key_title = "Risk"))) {
    expect_equal(hl_layout_report(plot)$legend_labels[1], "Risk")
  }
})

test_that("highlight greys the other groups and names unknown ones", {
  hl_use(brand = FALSE)
  data <- patients()
  rows <- spread_spec(data, "group", "lactate", highlight = "High")$rows
  colours <- stats::setNames(vapply(rows, `[[`, "", "color"), vapply(rows, `[[`, "", "name"))
  expect_equal(unname(colours[c("Low", "Mid")]), rep(context_colour(), 2))
  expect_equal(unname(colours["High"]), hl_palette()[3])
  expect_error(hl_raincloud(data, "group", "lactate", highlight = "Top"), "highlight names 'Top', which is not a group")
})

test_that("min_n leaves out small groups and names them", {
  hl_use(brand = FALSE)
  data <- rbind(patients(), data.frame(group = "Rare", site = "North", sofa = 3, lactate = 2))
  for (plot in list(hl_bars(data, "group", min_n = 5), hl_scatter(data, "sofa", "lactate", by = "group", min_n = 5))) {
    expect_match(plot@labels$caption, "Not shown (under 5): Rare.", fixed = TRUE)
  }
})

test_that("reference lines reach the drawn charts", {
  hl_use(brand = FALSE)
  expect_true("Upper normal" %in% drawn_texts(hl_spread(patients(), "group", "lactate", reference = c(`Upper normal` = 2))))
  rates <- data.frame(unit = c("A", "B"), rate = c(0.1, 0.2), low = c(0.05, 0.1), high = c(0.2, 0.3))
  expect_true("Target" %in% drawn_texts(hl_dotplot(rates, "unit", "rate", "low", "high", reference = c(Target = 0.15))))
})

test_that("facets draw panels or blocks", {
  hl_use(brand = FALSE)
  data <- patients()
  expect_length(hl_layout_report(hl_scatter(data, "sofa", "lactate", facet = "site"))$panels, 2)
  expect_length(hl_layout_report(hl_raincloud(data, "group", "lactate", facet = "site"))$panels, 2)
  shown <- drawn_texts(hl_spread(data, "group", "lactate", facet = "site"))
  expect_true(all(c("North", "South", "Low") %in% shown))
  expect_false("North · Low" %in% shown)
  expect_error(hl_spread(data, "group", "lactate", facet = "site", section = "site"), "facet and section both draw blocks")
})

test_that("the dot plot takes order, min_n and facets", {
  hl_use(brand = FALSE)
  rates <- data.frame(unit = rep(c("A", "B", "C"), 2), year = rep(c("2024", "2025"), each = 3),
                      rate = rep(c(0.1, 0.2, 0.3), 2), n = rep(c(50, 40, 3), 2))
  plot <- hl_dotplot(rates, "unit", "rate", n = "n", min_n = 10, facet = "year", order = c("B", "A"))
  expect_match(plot@labels$caption, "Not shown (under 10): C, C.", fixed = TRUE)
  expect_true(all(c("2024", "2025") %in% drawn_texts(plot)))
  expect_error(hl_dotplot(rates, "unit", "rate", min_n = 10), "min_n needs n =")
})

test_that("ridgeline facets draw panels with their n", {
  hl_use(brand = FALSE)
  plot <- hl_ridgeline(patients(), "group", "lactate", facet = "site", show_n = TRUE)
  expect_length(hl_layout_report(plot)$panels, 2)
  parts <- ggplot2::ggplotGrob(plot)$parts
  headers <- lapply(1:2, function(index) panel_header_for(parts, index))
  expect_equal(vapply(headers, `[[`, "", "name"), c("North", "South"))
  expect_equal(unname(unlist(lapply(headers, `[[`, "stats"))), c("45", "45"))
})

test_that("show_n = FALSE leaves n out of the dot plot and Likert", {
  hl_use(brand = FALSE)
  rates <- data.frame(unit = c("A", "B"), rate = c(0.1, 0.2), n = c(50, 40))
  expect_true("A (n = 50)" %in% drawn_texts(hl_dotplot(rates, "unit", "rate", n = "n")))
  shown <- drawn_texts(hl_dotplot(rates, "unit", "rate", n = "n", show_n = FALSE, min_n = 45))
  expect_true("A" %in% shown)
  expect_false(any(c("A (n = 50)", "B") %in% shown))
  ratings <- data.frame(item = rep(c("Clear", "Kind"), each = 20), rating = rep(1:5, 8))
  expect_true("n" %in% trimws(drawn_texts(hl_likert(ratings, "item", "rating"))))
  expect_false("n" %in% trimws(drawn_texts(hl_likert(ratings, "item", "rating", show_n = FALSE))))
})

test_that("the ridgeline keeps room for reference labels", {
  hl_use(brand = FALSE)
  top <- function(reference) {
    ggplot2::layer_scales(hl_ridgeline(patients(), "group", "lactate", reference = reference))$y$limits[2]
  }
  expect_gt(top(c(`Upper normal` = 2)), top(2))
})
