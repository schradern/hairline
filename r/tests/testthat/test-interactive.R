test_that("html export holds the svg, targets, script and font", {
  skip_if_not_installed("svglite")
  hl_use(brand = FALSE)
  data <- data.frame(x = rep(0:2, 2), y = c(1, 3, 2, 2, 1, 3), group = rep(c("North", "South"), each = 3))
  plot <- ggplot2::ggplot(data, ggplot2::aes(x, y, colour = group)) + ggplot2::geom_line() +
    ggplot2::labs(title = "Two series") + theme_hairline()
  path <- hl_save(plot, file.path(withr::local_tempdir(), "lines"), formats = "html")
  html <- paste(readLines(path, encoding = "UTF-8", warn = FALSE), collapse = "\n")
  expect_true(startsWith(html, "<!doctype html>") && grepl("<svg", html, fixed = TRUE) &&
                grepl("@font-face", html, fixed = TRUE))
  targets <- interactive_targets(plot)
  expect_equal(vapply(targets$series, `[[`, character(1), "name"), c("North", "South"))
  expect_equal(targets$series[[1]]$tips[[2]]$text, "North: 1, 3")
  expect_equal(vapply(targets$legend, `[[`, character(1), "name"), c("North", "South"))
})

test_that("fit lines stay static and points are targets", {
  hl_use(brand = FALSE)
  data <- data.frame(x = 1:6, y = c(1, 2.2, 2.9, 4.1, 5.2, 5.8))
  targets <- interactive_targets(hl_scatter(data, "x", "y", fit = "linear"))
  expect_length(targets$series, 1)
  expect_length(targets$series[[1]]$tips, 6)
})

test_that("the html figure is named by its title and subtitle", {
  skip_if_not_installed("svglite")
  hl_use(brand = FALSE)
  data <- data.frame(x = 0:2, y = c(1, 3, 2))
  plot <- ggplot2::ggplot(data, ggplot2::aes(x, y)) + ggplot2::geom_line() +
    ggplot2::labs(title = "Two series", subtitle = "Weekly <counts>") + theme_hairline()
  path <- hl_save(plot, file.path(withr::local_tempdir(), "named"), formats = "html")
  html <- paste(readLines(path, encoding = "UTF-8", warn = FALSE), collapse = "\n")
  expect_true(grepl('aria-label="Two series. Weekly &lt;counts>"', html, fixed = TRUE))
})

power_curve <- function(...) {
  hl_use(brand = FALSE)
  data <- data.frame(n = c(40, 80, 120, 160), power = c(0.05, 0.42, 0.896, 1))
  ggplot2::ggplot(data, ggplot2::aes(n, power)) + ggplot2::geom_line() +
    ggplot2::labs(title = "Power") + theme_hairline() + scale_y_hairline(percent = TRUE, ...)
}

tip_texts <- function(plot) vapply(interactive_targets(plot)$series[[1]]$tips, `[[`, character(1), "text")

test_that("scale digits reach the tooltips", {
  expect_equal(tip_texts(power_curve(digits = 1)), c("Power: 40, 5.0%", "Power: 80, 42.0%", "Power: 120, 89.6%",
                                                   "Power: 160, 100.0%"))
})

test_that("tooltip digits default to the shared rule", {
  expect_equal(tip_texts(power_curve())[3], "Power: 120, 90%")
})

test_that("scale digits leave the axis labels alone", {
  labels <- function(plot) ggplot2::ggplot_build(plot)@layout$panel_params[[1]]$y$get_labels()
  expect_equal(labels(power_curve(digits = 1)), labels(power_curve()))
})

test_that("scale digits apply to plain numbers on either axis", {
  hl_use(brand = FALSE)
  data <- data.frame(dose = c(0.5, 1.25, 2), response = c(1.5, 2.25, 3.125))
  plot <- ggplot2::ggplot(data, ggplot2::aes(dose, response)) + ggplot2::geom_line() +
    ggplot2::labs(title = "Response") + theme_hairline() + scale_y_hairline(digits = 2) +
    scale_x_hairline(digits = 0)
  expect_equal(tip_texts(plot), c("Response: 1, 1.50", "Response: 1, 2.25", "Response: 2, 3.13"))
})

test_that("scale digits must be a whole number from zero", {
  for (digits in list(-1, 1.5, "1", TRUE, NA_real_)) {
    expect_error(scale_y_hairline(digits = digits), "digits must be a whole number from 0 to 10")
  }
})

gallery_r <- function() normalizePath(test_path("..", "..", "..", "gallery"), mustWork = FALSE)
gallery_scripts <- function() {
  scripts <- list.files(file.path(gallery_r(), "r"), pattern = "\\.R$")
  sub("\\.R$", "", setdiff(scripts, "common.R"))
}
# Its HTML export is a real <table>, read as text: it has no marks to hover.
without_tips <- "table_characteristics"

# The plots a gallery script makes, with their sizes, collected where it would save them.
gallery_plots <- function(name) {
  withr::local_dir(gallery_r())
  previous <- hairline_state$settings
  on.exit(hairline_state$settings <- previous, add = TRUE)
  found <- list()
  script <- new.env(parent = globalenv())
  script$source <- function(file, ...) {
    sys.source(file, envir = script)
    script$finish <- function(plot, name, size) found[[length(found) + 1]] <<- list(plot = plot, size = size)
  }
  sys.source(file.path("r", paste0(name, ".R")), envir = script)
  found
}

# The series a plot exports without a tooltip, or "no series" when it exports none.
untipped <- function(plot, size = NULL) {
  series <- interactive_targets(plot, size = size)$series
  if (!length(series)) return("no series")
  vapply(Filter(function(entry) !length(entry$tips), series), `[[`, character(1), "name")
}

test_that("every gallery figure exports a tooltip per series", {
  skip_if(!length(gallery_scripts()), "the census runs the gallery scripts of the repository")
  skip_if_not_installed("svglite")
  for (name in gallery_scripts()) {
    plots <- gallery_plots(name)
    expect_true(length(plots) > 0, label = name)
    for (made in plots) {
      if (name %in% without_tips) {
        expect_null(made$plot@meta$hairline_targets, label = name)
      } else {
        expect_identical(untipped(made$plot, made$size), character(), label = name)
      }
    }
  }
})

test_that("every chart has a gallery figure, so the census reaches it", {
  skip_if(!length(gallery_scripts()), "the census runs the gallery scripts of the repository")
  charts <- c("arcs", "bars", "chord", "correlation", "donut", "dotplot", "forest", "funnel", "kaplan_meier",
              "lanes", "levels", "likert", "partition", "prisma", "raincloud", "ridgeline", "risk_of_bias", "sankey",
              "scatter", "spread", "swatches", "swimlanes", "table", "timeseries", "venn")
  exported <- sub("^hl_", "", grep("^hl_", getNamespaceExports("hairline"), value = TRUE))
  expect_true(all(charts %in% exported))
  scripts <- paste(vapply(list.files(file.path(gallery_r(), "r"), full.names = TRUE), function(path) {
    paste(readLines(path, warn = FALSE), collapse = "\n")
  }, character(1)), collapse = "\n")
  expect_identical(charts[!vapply(paste0("hl_", charts, "("), grepl, logical(1), scripts, fixed = TRUE)],
                   character())
})

census_cohort <- function(count = 40) {
  set.seed(3)
  data.frame(arm = rep(c("Standard", "Early"), each = count / 2), age = round(stats::rnorm(count, 64, 10)),
             sex = sample(c("F", "M"), count, TRUE), months = round(stats::rexp(count, 1 / 12), 1),
             died = sample(0:1, count, TRUE), date = format(as.Date("2025-01-01") + seq_len(count) - 1))
}

test_that("study figures export a tooltip per group", {
  hl_use(brand = FALSE)
  study <- suppressWarnings(hl_study(census_cohort(), group = "arm", time = "months", event = "died",
                                     variables = c("age", "sex")))
  effects <- data.frame(study = "age", estimate = 1.2, low = 1, high = 1.5)
  results <- suppressWarnings(list(hl_describe(study), hl_distribution(study, "age"), hl_compare(study, "age"),
                                   hl_compare(study, "sex"), hl_survival(study), hl_over_time(study, "date", "age"),
                                   hl_effects(study, effects, measure = "OR")))
  for (result in results) expect_identical(untipped(result$figure), character())
  names <- vapply(interactive_targets(results[[1]]$figure)$series, `[[`, character(1), "name")
  expect_setequal(names, c("Standard", "Early"))
})

census_stays <- function(count = 24) {
  set.seed(11)
  data.frame(unit = rep(c("Surgical", "Medical", "Neuro"), each = count), year = rep(c("2024", "2025"), count * 1.5),
             days = round(stats::rgamma(count * 3, 3, 0.5), 1))
}

series_named <- function(plot) {
  series <- interactive_targets(plot)$series
  stats::setNames(series, vapply(series, `[[`, character(1), "name"))
}

test_that("a raincloud tips each group's numbers, its points and nothing clipped or too small", {
  hl_use(brand = FALSE)
  data <- rbind(census_stays(), data.frame(unit = "Burns", year = "2025", days = c(3, 4)))
  data$days[1] <- 400
  series <- series_named(hl_raincloud(data, "unit", "days", summary = c("median", "iqr"), stats = "ci",
                                      compare = "Surgical", clip = c(NA, 100), min_n = 5))
  expect_identical(names(series), c("Surgical", "Medical", "Neuro"))
  surgical <- vapply(series$Surgical$tips, `[[`, character(1), "text")
  expect_match(surgical[1], "^Surgical: Median .*, IQR .*, 95% CI .*, n 24, Δ Reference, p –$")
  expect_length(surgical, 24)
  expect_false("Surgical: 400.0" %in% surgical)
})

test_that("ridges tip their numbers per facet panel and prisma boxes theirs without covering the text", {
  hl_use(brand = FALSE)
  series <- series_named(hl_ridgeline(census_stays(), "unit", "days", facet = "year", stats = "median"))
  expect_identical(sub("^.*, n ", "", vapply(series$Neuro$tips, `[[`, character(1), "text")), c("12", "12"))
  boxes <- series_named(hl_prisma(list(identified = 120, duplicates = 20, screened = 100, excluded = 70,
                                       assessed = 30, excluded_reasons = list(`Wrong population` = 8, `No control` = 4),
                                       included = 18)))
  expect_identical(boxes[["Reports excluded"]]$tips[[1]]$text,
                   "Reports excluded:\nWrong population (n = 8)\nNo control (n = 4)")
  expect_true(all(vapply(unlist(lapply(boxes, `[[`, "marks"), recursive = FALSE), function(mark) isTRUE(mark$hit),
                         logical(1))))
})
