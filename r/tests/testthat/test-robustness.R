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

test_that("a median on a flat half is the middle of the flat, as survfit takes it", {
  expect_equal(km_median(km_estimate(1:4, c(1, 1, 1, 1))), 2.5)
  expect_equal(km_median(km_estimate(1:4, c(1, 1, 0, 0))), 2)
})

# Second stress test

test_that("numbers beyond their precision do not round up, and non-finite ones read plainly", {
  expect_equal(hl_format_number(999999999999999.4, 0, "en"), "999,999,999,999,999")
  expect_equal(hl_format_number(1234567.345, 2, "en"), "1,234,567.35")
  expect_equal(hl_format_number(NA), "–")
  expect_equal(hl_format_number(Inf, 0, "de"), "∞")
  expect_error(hl_format_interval(c(1, 2), 0.5, 3), "formats one estimate")
})

test_that("small or tight values keep their digits, and small whole medians their half", {
  expect_equal(auto_digits(c(0.0004, 0.0003, 0.0005)), 4)
  expect_equal(auto_digits(c(1000.1, 1000.2, 1000.3)), 1)
  expect_equal(numeric_summary(c(1, 2, 3, 4), "median_iqr", 0, 0, whole = TRUE), "2.5 (1.8–3.3)")
  expect_equal(numeric_summary(c(55, 56, 61, 70), "median_iqr", 0, 0, whole = TRUE), "59 (56–63)")
})

test_that("bar labels keep the data's decimals and order leaves out what it does not name", {
  built <- ggplot2::ggplot_build(hl_bars(data.frame(g = c("A", "B"), v = c(0.25, 0.5)), "g", "v"))
  expect_setequal(unlist(lapply(built@data[-1], `[[`, "label")), c("0.25", "0.50"))
  data <- data.frame(u = rep(c("Ward", "ICU", "ED"), each = 2), n = 1:6)
  bars <- ggplot2::ggplot_build(hl_bars(data, "u", "n", order = "ICU"))@data[[1]]
  expect_equal(bars$y, 7)
  expect_error(hl_bars(data, "u", "n", order = "Theatre"), "order names 'Theatre'")
})

test_that("a missing group label is named", {
  data <- data.frame(arm = c("A", NA, "B"), n = c(30, 10, 60))
  expect_error(hl_bars(data, "arm", "n"), "'arm' is missing in row 2")
  expect_error(hl_donut(data, "arm", "n"), "'arm' is missing in row 2")
  expect_error(hl_raincloud(data, "arm", "n"), "'arm' is missing in row 2")
})

test_that("flows skip missing values, refuse self-flows and combine both directions of an arc", {
  data <- data.frame(s = c("A", "A", "B"), t = c("x", "x", "x"), v = c(5, NA, 3))
  expect_equal(sort(vapply(chord_spec(data, "s", "t", "v")$links, `[[`, numeric(1), "value")), c(3, 5))
  expect_error(chord_spec(data.frame(s = c("A", "A"), t = c("A", "B"), v = c(10, 1)), "s", "t", "v"),
               "flows to itself")
  spec <- arcs_spec(data.frame(s = c("A", "B"), t = c("B", "A"), v = c(2, 3)), "s", "t", "v")
  expect_equal(spec$links[[1]]$pair, "A ↔ B")
  expect_equal(spec$links[[1]]$value, 5)
})

test_that("log-rank follows survdiff where groups have no expected events", {
  expect_true(is.na(logrank_test(1:6, c(0, 0, 0, 0, 1, 0), rep(c("A", "B", "C"), each = 2))$p))
  expect_true(is.na(logrank_test(rep(3, 6), rep(1, 6), rep(c("A", "B", "C"), each = 2))$p))
  expect_equal(logrank_test(1:6, rep(1, 6), letters[1:6])$p, 0.09259092767611, tolerance = 1e-9)
  expect_no_error(hl_kaplan_meier(data.frame(time = 1:3, event = c(1, 1, 0), arm = "A"), "time", "event",
                                  by = "arm"))
})

test_that("forest refuses values it cannot draw and gives small values their digits", {
  rows <- data.frame(study = "S", estimate = 5, low = 0.9, high = 1.6)
  expect_error(hl_forest(rows), "outside its interval")
  expect_error(hl_forest(transform(rows, estimate = NA)), "must be numbers")
  expect_error(hl_forest(transform(rows, estimate = 1), favours = "A"), "favours takes two labels")
  tiny <- data.frame(study = "S", estimate = 0.0004, low = 0.0003, high = 0.0005)
  spec <- forest_spec(tiny, "study", "estimate", "low", "high", ratio = FALSE, colour = "#000000")
  expect_equal(spec$rows[[1]]$effect_text, "0.0004 [0.0003; 0.0005]")
  expect_equal(anyDuplicated(spec$axis$labels), 0L)
})

test_that("egger needs three studies with different errors", {
  expect_true(is.na(egger_p(c(0.1, 0.2), c(0.1, 0.2))))
  expect_true(is.na(egger_p(c(0.1, 0.2, 0.3), c(0.1, 0.1, 0.1))))
})

test_that("scatter fits the points it draws and gives the slope two significant digits", {
  data <- data.frame(x = 0:29, y = (0:29) %% 7, g = rep(c("A", "B", "C"), 10))
  plot <- hl_scatter(data, "x", "y", by = "g", order = c("A", "B"))
  expect_equal(plot@meta$hairline_headers[[1]]$stats[["n"]], "20")
  expect_equal(significant_places(0.000407), 5)
})

test_that("survival medians gain decimals for short times", {
  expect_equal(median_digits(list(km_estimate(c(0.01, 0.02, 0.03, 0.05), c(1, 1, 1, 0)))), 2)
})

test_that("study refuses what it cannot summarise and names unknown columns", {
  data <- data.frame(g = rep(c("a", "b"), 3), x = c(1.5, 2, 3, 4, 5, 6), a = 1:6,
                     day = as.Date("2025-01-01") + 0:5)
  study <- suppressWarnings(hl_study(data, group = "g", types = c(a = "categorical")))
  expect_equal(study$variables, c("x", "a"))
  expect_error(hl_compare(study, "nope"), "'nope' is not a column of the study")
  expect_error(hl_study(data[0, ], group = "g"), "no rows")
  expect_error(suppressWarnings(hl_study(data, types = list(x = "banana"))), "type 'banana'")
})

test_that("iso dates with a zone are read in UTC, and timeseries reads iso text as dates", {
  times <- study_iso_dates(c("2025-01-01T10:00:00Z", "2025-01-01T11:00+01:00"), "x")
  expect_equal(times[1], times[2])
  plot <- hl_timeseries(data.frame(day = c("2025-01-01", "2025-01-02", "2025-01-03"), v = 1:3), "day", "v")
  expect_true(inherits(plot@data$day, "Date"))
})

test_that("save refuses sizes that would crash the device and reads formats as given", {
  plot <- ggplot2::ggplot() + ggplot2::labs(title = "T") + theme_hairline()
  folder <- withr::local_tempdir()
  expect_error(hl_save(plot, file.path(folder, "a"), formats = "png", width_mm = -5), "width_mm must be a number")
  expect_error(hl_save(plot, file.path(folder, "a"), formats = "png", dpi = 0), "dpi must be a number")
  expect_equal(basename(hl_save(plot, file.path(folder, "b"), formats = c("PNG", "png"), dpi = 72)), "b.png")
  expect_error(hl_use(base_size = 0), "base_size must be a number above zero")
})

test_that("ridgeline shows constant groups and venn leaves missing values out", {
  data <- data.frame(g = rep(c("A", "B"), each = 10), v = c(rep(5, 10), seq(0, 1, length.out = 10)))
  built <- ggplot2::ggplot_build(hl_ridgeline(data, "g", "v"))
  expect_true(any(vapply(built@data, function(layer) "xend" %in% names(layer) && any(layer$x == 5), logical(1))))
  codes <- venn_member_codes(list(A = c(1, 2, NA), B = c(2, NA, NA)))
  expect_equal(length(codes), 2)
})

test_that("a real Other joins the folded Other slice", {
  folded <- fold_other(c(LETTERS[1:7], "Other", "H"), c(9, 8, 7, 6, 5, 4, 3, 100, 1))
  expect_equal(folded$labels, c(LETTERS[1:6], "Other"))
  expect_equal(folded$values[7], 104)
})

test_that("upright arc labels keep their room when the figure fits its height", {
  data <- data.frame(g = c("Intensive care unit of the university hospital", "Ward B"), h = c("z", "w"), v = 1:2)
  plot <- hl_arcs(data, "g", "h", "v")
  height <- fitted_size_mm(plot_for_size(plot, "onehalf"), figure_size_mm("onehalf", NULL, NULL))[2]
  expect_gt(height, 145 / 72 * 25.4)
  expect_no_error(hl_layout_report(plot))
})
