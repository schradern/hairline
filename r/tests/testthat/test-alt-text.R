alt_fixture_frame <- function(case) {
  as.data.frame(lapply(case$data, function(values) {
    if (is.character(unlist(values))) unlist(values) else vapply(values, function(value) value %||% NA_real_, 0)
  }), stringsAsFactors = FALSE)
}

alt_fixture_check <- function(cases, draw) {
  on.exit(hl_use(brand = FALSE))
  for (case in cases) {
    hl_use(brand = FALSE, locale = case$locale)
    options <- lapply(case$options, function(value) if (is.list(value)) unlist(value) else value)
    plot <- draw(alt_fixture_frame(case), options)
    expect_equal(figure_alt(plot), case$alt, info = paste(case$locale, names(case$options), collapse = " "))
  }
}

test_that("bar alt text matches the shared fixture, in English and German", {
  alt_fixture_check(read_fixture("alt_text.json")$bars,
                    function(data, options) do.call(hl_bars, c(list(data, "unit", "n"), options)))
})

test_that("time series alt text matches the shared fixture, in English and German", {
  alt_fixture_check(read_fixture("alt_text.json")$timeseries,
                    function(data, options) do.call(hl_timeseries, c(list(data, "t", "v"), options)))
})

test_that("distribution alt text matches the shared fixture, in English and German", {
  cases <- read_fixture("alt_text.json")$distributions
  charts <- list(spread = hl_spread, raincloud = hl_raincloud, ridgeline = hl_ridgeline)
  for (chart in names(charts)) {
    alt_fixture_check(Filter(function(case) identical(case$chart, chart), cases),
                      function(data, options) do.call(charts[[chart]], c(list(data, "unit", "days"), options)))
  }
})

test_that("Kaplan-Meier alt text matches the shared fixture, in English and German", {
  alt_fixture_check(read_fixture("alt_text.json")$kaplan_meier,
                    function(data, options) do.call(hl_kaplan_meier, c(list(data, "t", "e"), options)))
})

test_that("forest alt text matches the shared fixture, in English and German", {
  alt_fixture_check(read_fixture("alt_text.json")$forest,
                    function(data, options) do.call(hl_forest, c(list(data), options)))
})

test_that("dot plot alt text matches the shared fixture, in English and German", {
  alt_fixture_check(read_fixture("alt_text.json")$dotplot,
                    function(data, options) do.call(hl_dotplot, c(list(data), options)))
})

test_that("scatter alt text matches the shared fixture, in English and German", {
  alt_fixture_check(read_fixture("alt_text.json")$scatter,
                    function(data, options) do.call(hl_scatter, c(list(data, "x", "y"), options)))
})

test_that("donut alt text matches the shared fixture, in English and German", {
  alt_fixture_check(read_fixture("alt_text.json")$donut,
                    function(data, options) do.call(hl_donut, c(list(data), options)))
})

test_that("Likert alt text matches the shared fixture, in English and German", {
  alt_fixture_check(read_fixture("alt_text.json")$likert,
                    function(data, options) do.call(hl_likert, c(list(data, "item", "rating"), options)))
})

test_that("Sankey alt text matches the shared fixture, in English and German", {
  alt_fixture_check(read_fixture("alt_text.json")$sankey,
                    function(data, options) do.call(hl_sankey, c(list(data), options)))
})

test_that("chord alt text matches the shared fixture, in English and German", {
  alt_fixture_check(read_fixture("alt_text.json")$chord,
                    function(data, options) do.call(hl_chord, c(list(data, "source", "target"), options)))
})

test_that("Venn alt text matches the shared fixture, in English and German", {
  alt_fixture_check(read_fixture("alt_text.json")$venn,
                    function(data, options) do.call(hl_venn, c(list(data), options)))
})

test_that("correlation alt text matches the shared fixture, in English and German", {
  alt_fixture_check(read_fixture("alt_text.json")$correlation,
                    function(data, options) do.call(hl_correlation, c(list(data), options)))
})

test_that("funnel alt text matches the shared fixture, in English and German", {
  alt_fixture_check(read_fixture("alt_text.json")$funnel,
                    function(data, options) do.call(hl_funnel, c(list(data), options)))
})

test_that("PRISMA alt text matches the shared fixture, in English and German", {
  on.exit(hl_use(brand = FALSE))
  for (case in read_fixture("alt_text.json")$prisma) {
    hl_use(brand = FALSE, locale = case$locale)
    expect_equal(figure_alt(hl_prisma(case$counts)), case$alt, info = paste(case$locale, names(case$counts),
                                                                             collapse = " "))
  }
})

test_that("extremes name ties together and leave out missing values", {
  hl_use(brand = FALSE)
  expect_equal(alt_extremes(c("a", "b", "c", "d", "e"), c(2, NA, 5, 5, 1), c("2", "", "5", "5", "1")),
               "Highest: c, d (5); lowest: e (1).")
  expect_equal(alt_extremes(c("a", "b"), c(3, 3), c("3", "3")), "Every value 3.")
  expect_equal(alt_extremes("a", NA_real_, ""), "")
})

test_that("grid extremes name the first point reading row by row", {
  hl_use(brand = FALSE)
  grid <- matrix(c(1, 9, 9, NA), nrow = 2, byrow = TRUE)
  tips <- list(x = list("8", "12"), y = list("1", "2"), z = list(list("1", "9"), list("9", "")))
  expect_equal(alt_grid_extremes(grid, tips, list(x = "Hour", y = "Week")),
               "Highest at Hour 12, Week 1 (9); lowest at Hour 8, Week 1 (1).")
})

test_that("the alt text reaches the files and can be replaced", {
  hl_use(brand = FALSE)
  skip_if_not_installed("svglite")
  plot <- hl_bars(data.frame(unit = c("ICU", "Ward"), n = c(12, 30)), "unit", "n", title = "Admissions")
  expect_equal(hl_description(plot), "Bar chart. Highest: Ward (30); lowest: ICU (12).")
  path <- hl_save(plot, tempfile(), formats = "svg")
  svg <- paste(readLines(path, warn = FALSE), collapse = "")
  expect_match(svg, "<desc>Admissions. Bar chart. Highest: Ward (30); lowest: ICU (12).</desc>", fixed = TRUE)
  hl_description(plot) <- "Bar chart. The ward admits more than twice as many."
  expect_equal(figure_alt(plot), "Admissions. Bar chart. The ward admits more than twice as many.")
  hl_description(plot) <- NULL
  expect_equal(figure_alt(plot), "Admissions")
  expect_error(hl_description(plot) <- 3, "one text, or NULL")
})
