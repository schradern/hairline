survey_style <- function() drawing_style(hl_settings())

ratings <- function() {
  data.frame(section = rep(c("A", "B"), each = 8), statement = rep(c("Clear", "Rushed"), each = 8),
             rating = c(1, 3, 6, 7, 8, 9, 10, 10, 1, 1, 2, 2, 3, 6, 9, 10))
}

test_that("a ten-point scale reads in four bins with agreement cool", {
  hl_use(brand = FALSE)
  bins <- scale_bins(1:10, NULL, NULL)
  expect_equal(vapply(bins, `[[`, "", "name"), c("1–2", "3–5", "6–8", "9–10"))
  expect_equal(vapply(bins, `[[`, "", "side"), c("left", "left", "right", "right"))
  colours <- rev(interpolate_colors(hl_ramp(default_ramp("diverging")), 5))
  expect_equal(vapply(bins, `[[`, "", "color"), colours[c(1, 2, 4, 5)])
})

test_that("an odd scale centres its middle level and bins can be named", {
  hl_use(brand = FALSE)
  bins <- scale_bins(1:5, NULL, NULL)
  expect_equal(vapply(bins, `[[`, "", "side"), c("left", "left", "middle", "right", "right"))
  named <- scale_bins(1:10, NULL, list(low = c(1, 5), high = c(6, 10)))
  expect_equal(vapply(named, `[[`, "", "name"), c("low", "high"))
  expect_error(scale_bins(1:10, NULL, list(across = c(4, 7), rest = c(1, 3))),
               "bin 'across' must hold levels of one side")
})

test_that("reversed items are recoded and marked, rows carry their numbers", {
  hl_use(brand = FALSE)
  spec <- likert_spec(ratings(), "statement", "rating", levels = 1:10, group = "section", reverse = "Rushed")
  rushed <- spec$rows[[2]]
  expect_equal(rushed$name, "Rushed (reversed)")
  expect_equal(rushed$shares, c(25, 12.5, 12.5, 50))
  expect_equal(rushed$pairs, list(c("Median", "8"), c("IQR", "2–9"), c("n", "8")))
  expect_error(likert_spec(ratings(), "statement", "rating", reverse = "Missing"), "reverse names 'Missing'")
})

test_that("bins stack outward from the split and sections get headings", {
  hl_use(brand = FALSE)
  spec <- likert_spec(ratings(), "statement", "rating", levels = 1:10, group = "section")
  spans <- likert_segments(spec$rows[[1]], spec$bins)
  names(spans) <- vapply(spans, function(span) span$entry$name, "")
  expect_equal(c(spans[["3–5"]]$low, spans[["3–5"]]$high), c(-12.5, 0))
  shapes <- likert_drawing(spec, c(0, 0, 600, 200), measure_for(hl_settings()), survey_style())
  headings <- vapply(Filter(function(shape) identical(shape$part, "heading"), shapes), `[[`, "", "text")
  expect_equal(headings, c("A", "B"))
  tips <- unlist(lapply(shapes, `[[`, "tip"))
  expect_true("Clear: 9–10, 38%" %in% tips)
})

test_that("hl_likert puts its bins in the legend row and its segments in the tooltips", {
  hl_use(brand = FALSE)
  plot <- hl_likert(ratings(), "statement", "rating", levels = 1:10, key_title = "Rating")
  expect_equal(hl_layout_report(plot)$legend_labels, c("Rating", "1–2", "3–5", "6–8", "9–10"))
  names <- vapply(interactive_targets(plot)$series, `[[`, "", "name")
  expect_true(all(c("1–2", "9–10") %in% names))
})

importance <- function() {
  data.frame(area = c(rep("Booking", 8), rep("Records", 4)),
             feature = rep(c("Online", "Phone", "Results"), each = 4),
             rating = c(9, 10, 9, 8, 3, 5, 4, 6, 9, 8, 10, 9))
}

test_that("spread sections are lettered, sorted and marked with the mean", {
  hl_use(brand = FALSE)
  spec <- spread_spec(importance(), "feature", "rating", section = "area", panel_letters = TRUE, mean = TRUE,
                      sort = "median", stats = c("median", "n"), color_by = "area")
  expect_equal(vapply(spec$rows, `[[`, "", "name"), c("Online", "Phone", "Results"))
  expect_equal(spec$rows[[1]]$mean, 9)
  expect_equal(utils::tail(vapply(spec$legend, `[[`, "", "label"), 2), c("Median", "Mean"))
  shapes <- spread_drawing(spec, c(0, 0, 600, 200), measure_for(hl_settings()), survey_style())
  letters_drawn <- vapply(Filter(function(shape) identical(shape$part, "letter"), shapes), `[[`, "", "text")
  expect_equal(letters_drawn, c("a", "b"))
  expect_equal(sum(vapply(shapes, function(shape) identical(shape$role, "mean"), logical(1))), 3)
  expect_error(spread_spec(importance(), "feature", "rating", sort = "mean"), "sort 'mean' must be 'median'")
})

sources <- function() {
  data.frame(respondent = c(1, 1, 2, 3, 1, 2), question = c(rep("Sources", 4), "Topics", "Topics"),
             answer = c("Website", "Leaflet", "Website", "None", "Diet", "Costs"))
}

test_that("multiple choice counts respondents and greys the exclusive answer", {
  hl_use(brand = FALSE)
  plot <- hl_bars(sources(), "answer", facet = "question", respondents = "respondent", context = "None",
                  header = "n", horizontal = TRUE, size = "double")
  data <- plot@layers[[1]]$data
  first <- data[data$.facet == "Sources", ]
  expect_equal(sort(first$value), c(1, 1, 2) / 3)
  expect_equal(first$.alpha[first$.name == "None"], 0)
  expect_true(any(vapply(plot@layers, function(layer) isTRUE(layer$hairline_static), logical(1))))
  expect_equal(plot@meta$hairline_headers$Sources$stats, c(n = "3"))
  expect_equal(plot@labels$caption, "Several answers were possible.")
  expect_error(hl_bars(sources(), "answer", "respondent", respondents = "respondent"),
               "respondents counts one answer per row")
})

answers <- function() {
  data.frame(question = c("Recommend", "Recommend", "Reminder", "Reminder"),
             answer = c("Yes", "No", "Text", "Email"), count = c(30, 70, 55, 45))
}

test_that("answers are named inside, with an n column beside the bars", {
  hl_use(brand = FALSE)
  plot <- hl_bars(answers(), "question", "count", by = "answer", stacked = TRUE, percent = TRUE, sort = "given",
                  inside = "name", show_n = "column", size = "double")
  numbers <- plot@meta$hairline_side_numbers[[1]]
  expect_equal(vapply(numbers, `[[`, 0, "position"), c(2, 1))
  expect_equal(vapply(numbers, `[[`, "", "value"), c("100", "100"))
  texts <- sort(vapply(plot@meta$hairline_inside, `[[`, "", "text"))
  expect_equal(texts, c("Email 45%", "No 70%", "Text 55%", "Yes 30%"))
  names <- vapply(interactive_targets(plot, size = "double")$series, `[[`, "", "name")
  expect_setequal(names, c("Yes", "No", "Text", "Email"))
  plain <- hl_bars(answers(), "question", "count", by = "answer", stacked = TRUE, percent = TRUE, size = "double")
  expect_lt(hl_layout_report(plot)$panels[[1]][3], hl_layout_report(plain)$panels[[1]][3])
  expect_error(hl_bars(answers(), "question", "count", show_n = "column", horizontal = FALSE),
               "need horizontal bars")
})

test_that("hl_legend_ramp takes names and the legend an open diamond", {
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(data.frame(x = 1:2, y = 1:2), ggplot2::aes(x, y)) + ggplot2::geom_point() +
    ggplot2::labs(title = "Key") + theme_hairline() + hl_legend(list(list(kind = "diamond", colour = "#1b1e22",
                                                                          label = "Mean"))) +
    hl_legend_ramp(c("#111111", "#555555"), c(0.5, 1), "Rating", labels = c("low", "high"))
  expect_equal(hl_layout_report(plot, size = "double")$legend_labels, c("Mean", "Rating", "low", "high"))
  expect_error(hl_legend_ramp(c("#111111", "#555555"), c(0.5, 1), labels = "one"), "labels gives 1 names for 2 steps")
})
