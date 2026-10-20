# Inputs that once changed values, misrepresented data or lost files without an error.

test_that("exact values stay exact", {
  cases <- list(list(500000000, 0, "500,000,000"), list(1e9, 0, "1,000,000,000"), list(1e9, 2, "1,000,000,000.00"),
                list(1e6, 3, "1,000,000.000"), list(1234.499999, 0, "1,234"), list(8.645, 2, "8.65"),
                list(2.5, 0, "3"))
  for (case in cases) expect_equal(hl_format_number(case[[1]], case[[2]], "en"), case[[3]])
})

test_that("a label repeated under two parents counts once", {
  data <- data.frame(one = c("A", "B"), two = c("Shared", "Shared"), three = c("a", "b"), n = c(10, 30))
  rings <- donut_rings(data, NULL, "n", c("one", "two", "three"))
  totals <- vapply(rings, function(ring) sum(vapply(ring, `[[`, numeric(1), "value")), numeric(1))
  expect_equal(totals, c(40, 40, 40))
  expect_equal(vapply(rings[[3]], `[[`, character(1), "name"), c("a", "b"))
})

three_arms <- function() {
  data.frame(time = c(1:20, 2:21, seq_len(20) / 100), event = 1, arm = rep(c("A", "B", "C"), each = 20))
}

test_that("the log-rank test covers only the groups drawn", {
  plot <- hl_kaplan_meier(three_arms(), "time", "event", by = "arm", order = c("A", "B"))
  expect_equal(plot@meta$hairline_headers[[1]]$stats[["Log-rank"]], "p = 0.50")
})

test_that("study survival tests only the groups it reports", {
  study <- suppressWarnings(hl_study(three_arms(), group = "arm", time = "time", event = "event",
                                     order = c("A", "B")))
  result <- hl_survival(study)
  expect_equal(result$table$Group, c("A", "B"))
  expect_equal(result$values$p, "p = 0.50")
})

test_that("all-censored groups draw without a test", {
  data <- data.frame(time = 1:4, event = 0, arm = c("A", "A", "B", "B"))
  expect_true(is.na(logrank_test(data$time, data$event, data$arm)$p))
  plot <- hl_kaplan_meier(data, "time", "event", by = "arm")
  expect_equal(names(plot@meta$hairline_headers[[1]]$stats), "Median")
})

test_that("factor numbers are read by their labels", {
  data <- data.frame(months = factor(c("10", "20", "30")), died = 1, score = factor(c(10, 20, 30)))
  study <- suppressWarnings(hl_study(data, time = "months", event = "died", types = c(score = "numeric")))
  expect_equal(hl_survival(study)$values[["Overall"]], "20.0")
  expect_equal(study_numbers(data$score), c(10, 20, 30))
})

test_that("a failed save keeps the existing files", {
  folder <- withr::local_tempdir()
  existing <- file.path(folder, "figure.png")
  writeBin(charToRaw("old figure"), existing)
  testthat::local_mocked_bindings(write_html = function(...) stop("cannot read a missing value"))
  plot <- ggplot2::ggplot() + ggplot2::labs(title = "T") + theme_hairline()
  expect_error(hl_save(plot, file.path(folder, "figure"), formats = c("png", "html"), dpi = 72), "missing value")
  expect_equal(rawToChar(readBin(existing, "raw", 100)), "old figure")
  expect_equal(list.files(folder, all.files = TRUE, no.. = TRUE), "figure.png")
})

test_that("a folder in the way stops the save before writing", {
  folder <- withr::local_tempdir()
  existing <- file.path(folder, "figure.png")
  writeBin(charToRaw("old figure"), existing)
  dir.create(file.path(folder, "figure.html"))
  plot <- ggplot2::ggplot() + ggplot2::labs(title = "T") + theme_hairline()
  expect_error(hl_save(plot, file.path(folder, "figure"), formats = c("png", "html"), dpi = 72),
               "a folder of that name exists")
  expect_equal(rawToChar(readBin(existing, "raw", 100)), "old figure")
})

test_that("negative segments stack below zero and the total sits past the positive ones", {
  data <- data.frame(unit = "Ward", part = c("a", "b", "c"), change = c(5, -3, 2))
  built <- ggplot2::ggplot_build(hl_bars(data, "unit", "change", by = "part", stacked = TRUE, horizontal = FALSE))
  bars <- built@data[[1]]
  expect_equal(sort(c(bars$ymin, bars$ymax)), c(-3, 0, 0, 5, 5, 7))
  total <- Filter(function(layer) identical(layer$label, "4"), built@data)
  expect_equal(total[[1]]$y, 7)
})

test_that("missing values are left out of bar sums", {
  built <- ggplot2::ggplot_build(hl_bars(data.frame(unit = c("A", "A"), n = c(1, NA)), "unit", "n"))
  expect_equal(built@data[[1]]$y, 1)
})

test_that("percent bars refuse a category without a total", {
  data <- data.frame(unit = c("Ward", "Ward", "ICU"), part = c("a", "b", "a"), n = c(1, 2, 0))
  expect_error(hl_bars(data, "unit", "n", by = "part", stacked = TRUE, percent = TRUE), "'ICU' totals 0")
})

test_that("a count column in the data stays a category", {
  built <- ggplot2::ggplot_build(hl_bars(data.frame(Count = c("A", "A", "B")), "Count"))
  expect_equal(sort(built@data[[1]]$y), c(1, 2))
})

test_that("a long study label is refused rather than reversing the axis", {
  data <- data.frame(study = "Early mobilisation plus physiotherapy versus standard rehabilitation", estimate = 1,
                     low = 0.5, high = 2)
  expect_error(hl_layout_report(hl_forest(data), size = "onehalf"), "leave [0-9]+ pt for the intervals")
})

test_that("rolling means skip missing values and refuse invalid windows", {
  expect_equal(rolling_mean(c(1, NA, 3, 4), 2), c(1, 1, 3, 3.5))
  data <- data.frame(day = 1:3, value = c(2, 4, 8))
  for (window in list(0, -1, 1.5)) {
    expect_error(hl_timeseries(data, "day", "value", window = window), "window must be a whole number of 1 or more")
  }
})

test_that("iso dates refuse trailing text and keep clock times", {
  expect_error(study_iso_dates("2025-01-01garbage", "day"), "'2025-01-01garbage', which is not an ISO date")
  times <- study_iso_dates(c("2025-01-01T10:00", "2025-01-01 11:00:00", "2025-01-01 12:00"), "day")
  expect_equal(length(unique(times)), 3)
  expect_equal(study_iso_dates("2025-01-31", "day"), as.Date("2025-01-31"))
})

test_that("effects use the requested digits in the table and the figure", {
  study <- suppressWarnings(hl_study(data.frame(x = 1:3)))
  table <- data.frame(study = "Age", estimate = 1.23456, low = 0.45678, high = 2.34567)
  result <- hl_effects(study, table, digits = 4)
  expect_equal(result$table[[2]], "1.2346 [0.4568; 2.3457]")
  spec <- environment(result$figure@meta$hairline_drawing)$spec
  expect_equal(spec$rows[[1]]$effect_text, "1.2346 [0.4568; 2.3457]")
})

test_that("a one-group raincloud has no pairs to compare", {
  expect_no_error(hl_raincloud(data.frame(group = "A", value = c(1, 2, 3)), "group", "value", comparisons = "all"))
})

test_that("tests on identical samples read 'p not defined'", {
  expect_equal(format_p(rank_sum_p(c(1, 1, 1), c(1, 1, 1))), "p not defined")
  expect_equal(format_p(kruskal_p(list(c(2, 2), c(2, 2), c(2, 2)))), "p not defined")
})

test_that("prisma counts are whole and not negative", {
  for (value in c(-5, 3.4)) {
    expect_error(prisma_spec(list(identified = 10, screened = value, included = 2)),
                 "counts must be whole numbers of 0 or more")
  }
})

test_that("funnel refuses standard errors of zero or less", {
  data <- data.frame(ratio = c(0.8, 1.1, 0.9), se = c(0.2, -0.1, 0.3))
  expect_error(funnel_spec(data, "ratio", "se"), "'se' is -0.1 in row 2")
})

test_that("an interval needs both ends", {
  expect_error(hl_dotplot(data.frame(unit = "A", rate = 1, low = 0.5), "unit", "rate", low = "low"),
               "needs both low and high")
})

test_that("repeated judgements are refused", {
  data <- data.frame(study = c("S1", "S1", "S2"), domain = "D1", judgement = c("low", "low", "high"))
  expect_error(risk_of_bias_spec(data, "study", "domain", "judgement"), "S1 has 2 judgements for D1")
})

test_that("a fit without spread in x and a constant correlation column name their need", {
  expect_error(hl_scatter(data.frame(x = 1, y = 1), "x", "y"), "2 different x values")
  expect_error(correlation_spec(data.frame(a = 1:3, b = 5)), "'b' has the same value in every complete row")
})

test_that("missing follow-up times are refused", {
  expect_error(km_estimate(c(1, NA, 3), c(1, 1, 0)), "must not be missing; row 2")
})

test_that("raincloud leaves missing values out", {
  expect_no_error(ggplot2::ggplot_build(hl_raincloud(data.frame(group = "A", value = c(1, NA, 3)), "group",
                                                     "value")))
})

test_that("tooltips keep the locale the plot was made in", {
  hl_use(brand = FALSE, locale = "de")
  plot <- ggplot2::ggplot(data.frame(x = c(1.1, 2.2), y = c(1.1, 2.2)), ggplot2::aes(x, y)) + ggplot2::geom_line() +
    ggplot2::labs(title = "T") + theme_hairline()
  hl_use(brand = FALSE, locale = "en")
  tips <- vapply(interactive_targets(plot)$series[[1]]$tips, `[[`, character(1), "text")
  expect_match(tips[1], "1,1, 1,1", fixed = TRUE)
})

test_that("html embeds the requested font, not the bundled one", {
  fonts <- systemfonts::system_fonts()
  usable <- fonts[grepl("\\.ttf$", fonts$path, useBytes = TRUE) & fonts$family != hl_tokens()$font$family, ]
  skip_if(nrow(usable) == 0, "no installed TrueType font to embed")
  family <- usable$family[1]
  faces <- font_faces(family)
  expect_match(faces, sprintf("font-family:'%s'", family), fixed = TRUE)
  bundled <- vapply(hl_tokens()$interactive$fonts, function(file) {
    path <- system.file("fonts", file, package = "hairline")
    gsub("\n", "", jsonlite::base64_enc(readBin(path, "raw", file.info(path)$size)))
  }, character(1))
  for (data in bundled) expect_false(grepl(data, faces, fixed = TRUE))
})

tiff_text <- function(path, tag) {
  bytes <- readBin(path, "raw", file.size(path))
  little <- identical(rawToChar(bytes[1:2]), "II")
  start <- tiff_read(bytes, 4, 4, little)
  for (index in seq_len(tiff_read(bytes, start, 2, little)) - 1) {
    at <- start + 2 + index * 12
    if (tiff_read(bytes, at, 2, little) != tag) next
    count <- tiff_read(bytes, at + 4, 4, little)
    from <- if (count <= 4) at + 8 else tiff_read(bytes, at + 8, 4, little)
    return(rawToChar(bytes[from + seq_len(count - 1)]))
  }
  NULL
}

test_that("tiff names its figure", {
  plot <- ggplot2::ggplot() + ggplot2::labs(title = "Überleben", subtitle = "Nach Gruppe") + theme_hairline()
  path <- hl_save(plot, file.path(withr::local_tempdir(), "named"), formats = "tiff", dpi = 72)
  title <- tiff_text(path, 269)
  Encoding(title) <- "UTF-8"
  expect_equal(title, "Überleben")
  description <- tiff_text(path, 270)
  Encoding(description) <- "UTF-8"
  expect_equal(description, "Überleben. Nach Gruppe")
  expect_equal(tiff_read(readBin(path, "raw", 8), 0, 2, TRUE) %in% c(0x4949, 0x4d4d), TRUE)
})

test_that("html export skips missing values", {
  plot <- hl_timeseries(data.frame(day = 1:4, value = c(NA, 2, NA, 4)), "day", "value", window = 1)
  targets <- suppressWarnings(interactive_targets(plot))
  tips <- unlist(lapply(targets$series, function(series) vapply(series$tips, `[[`, character(1), "text")))
  expect_false(any(grepl("NA", tips, fixed = TRUE)))
})
