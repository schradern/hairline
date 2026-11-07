daylight <- function() unname(hl_tokens()$palettes$daylight)

procedures <- function() {
  rows <- expand.grid(year = as.character(2021:2026), group = c("Large", "Small"), stringsAsFactors = FALSE)
  rows$cases <- c(2, 12, 12, 12, 12, 10) * ifelse(rows$group == "Large", 300, 10)
  rows
}

doses <- function() {
  values <- c(rep(25, 12), rep(50, 12), 5000, 7500)
  data.frame(group = c(rep("Ward", length(values)), "Local anaesthetic"), mg = c(values, 10))
}

test_that("facets get their own value axis and a total in the header", {
  hl_use(brand = FALSE)
  plot <- hl_bars(procedures(), "year", "cases", facet = "group", sort = "given", size = "double")
  built <- ggplot2::ggplot_build(plot)
  tops <- vapply(built@layout$panel_params, function(params) params$y$continuous_range[2], numeric(1))
  expect_length(tops, 2)
  expect_gt(tops[1], 10 * tops[2])
  expect_equal(plot@meta$hairline_headers$Large$stats, c(Total = "18,000"))
  expect_equal(plot@meta$hairline_headers$Small$stats, c(Total = "600"))
})

test_that("shared scales give facets one value axis", {
  hl_use(brand = FALSE)
  built <- ggplot2::ggplot_build(hl_bars(procedures(), "year", "cases", facet = "group", scales = "shared",
                                         sort = "given", size = "double"))
  ranges <- lapply(built@layout$panel_params, function(params) params$y$continuous_range)
  expect_equal(ranges[[1]], ranges[[2]])
})

test_that("incomplete periods are drawn lighter and named in the caption, in the locale", {
  hl_use(brand = FALSE, locale = "de")
  on.exit(hl_use(brand = FALSE))
  plot <- hl_bars(procedures(), "year", "cases", facet = "group", sort = "given",
                  partial = c("2021" = "2 Monate", "2026" = "10 Monate"), caption = "Synthetische Daten.")
  data <- plot@layers[[1]]$data
  expect_equal(data$.alpha[data$.name %in% c("2021", "2026")], rep(hl_tokens()$partial$opacity, 4))
  expect_true(all(data$.alpha[!data$.name %in% c("2021", "2026")] == 1))
  expect_equal(plot@labels$caption,
               "Synthetische Daten. Unvollständig, heller: 2021 (2 Monate), 2026 (10 Monate).")
  expect_error(hl_bars(procedures(), "year", "cases", partial = c("2030" = "1 month")), "partial names '2030'")
})

test_that("top folds the rest into other per panel", {
  hl_use(brand = FALSE)
  data <- data.frame(place = rep(LETTERS[1:7], 2), group = rep(c("x", "y"), each = 7),
                     n = c(9, 8, 7, 1, 1, 1, 1, 1, 1, 1, 1, 5, 6, 7))
  plot <- hl_bars(data, "place", "n", facet = "group", top = 3, horizontal = FALSE)
  rows <- plot@layers[[1]]$data
  first <- rows[rows$.facet == "x", ]
  expect_equal(first$.name, c("A", "B", "C", "Other"))
  expect_equal(first$value, c(9, 8, 7, 4))
  second <- rows[rows$.facet == "y", ]
  expect_equal(utils::tail(as.character(sort(unique(second$category))), 1), "y\037Other")
})

test_that("show_n writes the n after the label while colours key on the bare group", {
  hl_use(brand = FALSE, locale = "de")
  on.exit(hl_use(brand = FALSE))
  data <- data.frame(unit = c(rep("A", 1200), rep("B", 3)))
  built <- ggplot2::ggplot_build(hl_bars(data, "unit", show_n = TRUE, horizontal = TRUE))
  expect_equal(built@layout$panel_params[[1]]$y$get_labels(), c("B (n = 3)", "A (n = 1 200)"))
})

test_that("normalize draws shares and keeps the n", {
  hl_use(brand = FALSE)
  data <- data.frame(unit = c("A", "A", "A", "B"), pattern = c("bolus", "bolus", "infusion", "bolus"))
  plot <- hl_bars(data, "unit", by = "pattern", stacked = TRUE, normalize = TRUE, horizontal = TRUE)
  expect_equal(sort(round(plot@layers[[1]]$data$value, 4)), c(0.3333, 0.6667, 1))
  built <- ggplot2::ggplot_build(plot)
  expect_equal(built@layout$panel_params[[1]]$y$get_labels(), c("B (n = 1)", "A (n = 3)"))
})

test_that("color_by colours groups by a coarser column and lists it in the legend", {
  hl_use(brand = FALSE)
  data <- data.frame(row = c("GA child", "GA adult", "RA child", "RA adult"), procedure = c("GA", "GA", "RA", "RA"),
                     n = c(3, 5, 2, 4), year = "2025")
  plot <- hl_bars(data, "year", "n", by = "row", color_by = "procedure")
  colours <- unique(ggplot2::ggplot_build(plot)@data[[1]][, c("group", "fill")])$fill
  expect_equal(colours[1], colours[2])
  expect_false(colours[2] == colours[3])
  expect_equal(hl_layout_report(plot)$legend_labels, c("GA", "RA"))
  bad <- data.frame(row = c("a", "a"), procedure = c("GA", "RA"), year = c("1", "1"))
  expect_error(hl_bars(bad, "year", by = "row", color_by = "procedure"), "gives 'a' more than one value")
})

test_that("a second dimension keeps off the slots the first holds", {
  hl_use(brand = FALSE)
  found <- colours_for(c("GA", "RA", "Sedation", "Combined"), dimension = "procedure")
  expect_equal(unname(found), daylight()[1:4])
  patterns <- colours_for(c("single bolus", "repeated", "infusion"), dimension = "pattern")
  expect_equal(unname(patterns), daylight()[5:7])
})

test_that("hl_scope gives charts inside their dimension", {
  hl_use(brand = FALSE)
  hl_bars(data.frame(procedure = c("GA", "RA"), n = 1:2), "procedure", "n", by = "procedure", dimension = "procedure")
  hl_scope("pattern", hl_bars(data.frame(pattern = c("bolus", "infusion"), n = 3:4), "pattern", "n", by = "pattern"))
  expect_equal(hl_color("bolus"), daylight()[3])
  expect_equal(hl_color("infusion"), daylight()[4])
})

test_that("a full palette names both dimensions", {
  hl_use(brand = FALSE, palette = c("#112233", "#445566", "#778899"))
  on.exit(hl_use(brand = FALSE))
  colours_for(c("a", "b"), dimension = "procedure")
  expect_error(colours_for(c("x", "y"), dimension = "pattern"),
               "held by dimension 'procedure' and 2 categories of dimension 'pattern'")
})

test_that("min_n leaves small groups out and names them, in the locale", {
  hl_use(brand = FALSE, locale = "de")
  on.exit(hl_use(brand = FALSE))
  spec <- spread_spec(doses(), "group", "mg", min_n = 10)
  expect_equal(vapply(spec$rows, `[[`, "", "name"), "Ward")
  expect_equal(spec$notes, "Nicht dargestellt (unter 10): Local anaesthetic.")
})

test_that("clip hides values outside the limits and says so", {
  hl_use(brand = FALSE)
  spec <- suppressWarnings(spread_spec(doses(), "group", "mg", min_n = 10, clip = c(NA, 1000),
                                       stats = c("median", "range", "n")))
  row <- spec$rows[[1]]
  expect_equal(row$high, 50)
  expect_equal(row$pairs[[3]], c("n", "26"))
  expect_equal(row$pairs[[2]], c("Range", "25–7,500"))
  expect_equal(utils::tail(spec$notes, 1), "2 values above 1,000 not drawn; the statistics use every value.")
  drawn <- suppressWarnings(spread_spec(doses(), "group", "mg", min_n = 10, clip = c(NA, 1000), clip_stats = TRUE,
                                        stats = "n"))
  expect_equal(drawn$rows[[1]]$pairs, list(c("n", "24")))
  expect_match(utils::tail(drawn$notes, 1), "the statistics use the values drawn.", fixed = TRUE)
})

test_that("a quantile clip takes the limit from every value", {
  hl_use(brand = FALSE)
  spec <- spread_spec(data.frame(group = "a", value = 0:99), "group", "value", clip = 0.95)
  expect_equal(spec$rows[[1]]$high, 94)
  expect_equal(spec$notes, "5 values above 94 not drawn; the statistics use every value.")
})

test_that("a median between two large levels is warned about, and levels show them", {
  hl_use(brand = FALSE)
  expect_warning(spec <- spread_spec(doses()[1:24, ], "group", "mg", stats = c("median", "levels")),
                 "the median of 'Ward', 37.5, lies between 25 and 50")
  expect_equal(spec$rows[[1]]$pairs[[2]], c("Levels", "25 (50%) · 50 (50%)"))
})

test_that("discrete quantiles stay on the levels and the caption says so", {
  hl_use(brand = FALSE)
  spec <- spread_spec(doses()[1:24, ], "group", "mg", discrete = TRUE, stats = c("median", "iqr"))
  expect_equal(spec$rows[[1]]$pairs[[1]], c("Median", "25"))
  expect_equal(spec$notes, "Quantiles on the data's own levels.")
  expect_equal(level_quantiles(c(1, 2, 2, 3, 3, 3, 4, 5, 5, 6), 0.9), 5)
})

test_that("ridgeline and raincloud leave small groups out and count what they show", {
  hl_use(brand = FALSE)
  data <- data.frame(group = c(rep("a", 30), "b"), value = c(seq_len(29), 900, 5))
  ridges <- hl_ridgeline(data, "group", "value", min_n = 5, clip = c(NA, 100), show_n = TRUE)
  expect_match(ridges@labels$caption, "Not shown (under 5): b.", fixed = TRUE)
  expect_match(ridges@labels$caption, "1 value above 100 not drawn", fixed = TRUE)
  expect_equal(ggplot2::ggplot_build(ridges)@layout$panel_params[[1]]$y$get_labels(), "a (n = 30)")
  rain <- hl_raincloud(data, "group", "value", min_n = 5, clip = c(NA, 100), clip_stats = TRUE)
  expect_equal(rain@meta$hairline_table$rows[[1]]$text, "n = 29")
})

test_that("scatter clips y and the dot plot writes each row's n", {
  hl_use(brand = FALSE)
  data <- data.frame(x = 1:10, y = c(1:9, 500))
  plot <- hl_scatter(data, "x", "y", clip = c(NA, 100))
  expect_equal(nrow(plot@layers[[1]]$data), 9)
  expect_equal(plot@labels$caption, "1 value above 100 not drawn; the statistics use every value.")
  units <- data.frame(unit = c("A", "B"), rate = c(0.1, 0.2), patients = c(1010, 20))
  shapes <- hl_dotplot(units, "unit", "rate", n = "patients")@meta$hairline_drawing(
    c(0, 0, 400, 160), measure_for(hl_settings()), drawing_style(hl_settings()))
  texts <- vapply(Filter(function(shape) shape$kind == "text", shapes), `[[`, "", "text")
  expect_true("A (n = 1,010)" %in% texts)
})

test_that("timeseries veils incomplete periods and names them", {
  hl_use(brand = FALSE)
  data <- data.frame(date = as.Date("2021-11-01") + 0:99, value = seq_len(100))
  plot <- hl_timeseries(data, "date", "value", partial = c("2021" = "2 months"))
  expect_equal(plot@labels$caption, "Incomplete, drawn lighter: 2021 (2 months).")
  geoms <- vapply(plot@layers, function(layer) class(layer$geom)[1], "")
  expect_true("GeomRect" %in% geoms)
})

test_that("a table formats numbers in the locale and aligns them right", {
  hl_use(brand = FALSE, locale = "de")
  on.exit(hl_use(brand = FALSE))
  data <- data.frame(Group = c("A", "B"), Cases = c(1841, 20), Share = c("12 %", "88 %"))
  spec <- table_spec(data, bold_rows = "B")
  expect_equal(spec$rows[[1]], c("A", "1 841", "12 %"))
  expect_equal(spec$align, c("left", "right", "right"))
  expect_equal(spec$bold, 2L)
  expect_error(table_spec(data, bold_rows = 5), "bold_rows names row 5")
  expect_error(table_spec(data, align = c(Nope = "left")), "align names 'Nope'")
})

test_that("a table indents rows, wraps its headings and writes an HTML table", {
  hl_use(brand = FALSE)
  data <- data.frame(Characteristic = c("Sex, n (%)", "  Female"), Overall = c("", "3 (60%)"))
  plot <- hl_table(data, "Characteristics", footnotes = "IQR: interquartile range.", caption = "Synthetic data.")
  expect_equal(plot@labels$caption, "IQR: interquartile range.\nSynthetic data.")
  shapes <- plot@meta$hairline_drawing(c(10, 10, 300, 100), measure_for(hl_settings()), drawing_style(hl_settings()))
  cells <- Filter(function(shape) shape$kind == "text", shapes)
  female <- Filter(function(shape) shape$text == "Female", cells)[[1]]
  expect_equal(female$x, 10 + hl_settings()$base_size)
  path <- tempfile()
  hl_save(plot, path, formats = "html")
  html <- paste(readLines(paste0(path, ".html"), warn = FALSE), collapse = "")
  expect_match(html, "<table><thead><tr><th", fixed = TRUE)
  expect_match(html, "padding-left:", fixed = TRUE)
})

test_that("a report numbers figures and tables apart, in the locale", {
  hl_use(brand = FALSE, locale = "de")
  on.exit(hl_use(brand = FALSE))
  table <- hl_table(data.frame(a = "x", b = 1), "Tabelle")
  figure <- hl_bars(data.frame(g = c("a", "b"), n = 1:2), "g", "n", title = "Balken")
  report <- hl_report_add(hl_report_add(hl_report_add(hl_report("Bericht"), figure), table), figure, "Noch einmal.")
  labels <- vapply(report_numbered(report), `[[`, "", "label")
  expect_equal(labels, c("Abbildung 1", "Tabelle 1", "Abbildung 2"))
  path <- hl_report_write(report, tempfile(fileext = ".html"))
  html <- paste(readLines(path, warn = FALSE), collapse = "")
  expect_match(html, "<b>Abbildung 2.</b> Noch einmal.", fixed = TRUE)
  expect_match(html, "<table>", fixed = TRUE)
  expect_error(hl_report_write(report, tempfile(fileext = ".pdf")), "makes .md or .html files")
})

test_that("describe warns when a median falls between two large levels", {
  hl_use(brand = FALSE)
  data <- data.frame(arm = "A", dose = c(10, rep(25, 12), rep(50, 12), 100))
  study <- suppressWarnings(hl_study(data, group = "arm", variables = "dose"))
  expect_warning(expect_warning(hl_describe(study), "the median of Dose in A lies between 25 and 50"),
                 "the median of Dose in Overall")
})
