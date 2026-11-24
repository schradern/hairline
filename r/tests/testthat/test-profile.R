# One surgical cohort: numbers, categories, a missing weight and operation dates as ISO text.
profile_operations <- function(count = 120) {
  set.seed(3)
  weight <- round(stats::rnorm(count, 80, 14), 1)
  weight[5] <- NA
  data.frame(id = seq_len(count), sex = sample(c("Female", "Male"), count, TRUE),
             age = round(stats::rnorm(count, 60, 12)), weight = weight,
             asa = sample(c("ASA I", "ASA II", "ASA III"), count, TRUE), stay = 1 + stats::rpois(count, 4),
             arm = sample(c("A", "B"), count, TRUE),
             surgery_date = format(as.Date("2023-01-02") + sample(0:699, count, TRUE)), stringsAsFactors = FALSE)
}

profile_study <- function(data = profile_operations(), variables = c("age", "sex", "weight", "asa", "stay"), ...) {
  suppressWarnings(hl_study(data, id = "id", variables = variables,
                            labels = c(asa = "ASA class", stay = "Length of stay"),
                            units = c(age = "years", weight = "kg", stay = "days"), unit = "patients", ...))
}

tile_names <- function(figure) vapply(figure@meta$hairline_rows$plots, function(tile) {
  tile@meta$hairline_headers[[1]]$name
}, "")

test_that("hl_profile() is Table 1 of the whole cohort with a tile per variable", {
  hl_use(brand = FALSE)
  result <- hl_profile(profile_study(), dates = "surgery_date")
  expect_equal(names(result$table), c("Characteristic", "Overall"))
  expect_equal(unlist(result$table[1, ]), c(Characteristic = "n", Overall = "120"))
  expect_equal(result$table$Characteristic[nrow(result$table)], "Surgery date, first to last")
  expect_equal(result$text, "120 patients. Missing: Weight 1.")
  expect_equal(tile_names(result$figure), c("Age", "Sex", "Weight", "ASA class", "Length of stay", "Surgery date"))
  expect_equal(result$figure@meta$hairline_rows$columns, 3)
  expect_equal(result$figure@meta$hairline_rows$plots[[3]]@meta$hairline_headers[[1]]$qualifier, "1 missing")
  expect_equal(result$figure@meta$hairline_rows$plots[[6]]@meta$hairline_headers[[1]]$qualifier, "per month")
  expect_length(hl_check_layout(result$figure, size = "double"), 0)
})

test_that("hl_profile() tips every tile, naming the bin, level or period", {
  hl_use(brand = FALSE)
  series <- interactive_targets(hl_profile(profile_study(), dates = "surgery_date")$figure, size = "double")$series
  expect_equal(vapply(series, `[[`, "", "name"),
               c("Age", "Sex", "Weight", "ASA class", "Length of stay", "Surgery date"))
  stay <- series[[5]]
  expect_match(stay$tips[[1]]$text, "^Length of stay 1 days: ")
})

test_that("hl_profile(by =) splits every tile in the session's colours, one legend for all", {
  hl_use(brand = FALSE)
  data <- profile_operations()
  result <- hl_profile(profile_study(data), dates = "surgery_date", by = "sex")
  females <- sum(data$sex == "Female")
  expect_equal(names(result$table), c("Characteristic", "Female", "Male", "Overall"))
  expect_true(startsWith(result$text, sprintf("120 patients; by sex, %d Female and %d Male.", females, 120 - females)))
  first <- result$figure@meta$hairline_rows$plots[[1]]
  expect_equal(vapply(first@meta$hairline_legend, `[[`, "", "label"), c("Female", "Male"))
  expect_equal(first@meta$hairline_key_title, "Sex")
  series <- interactive_targets(result$figure, size = "double")$series
  expect_setequal(vapply(series, `[[`, "", "name"), c("Female", "Male"))
  expect_length(hl_check_layout(result$figure, size = "double"), 0)
})

test_that("hl_profile(by =) keeps rows without a group as Missing, in grey", {
  hl_use(brand = FALSE)
  data <- profile_operations()
  data$sex[1:3] <- NA
  result <- hl_profile(profile_study(data), by = "sex")
  legend <- result$figure@meta$hairline_rows$plots[[1]]@meta$hairline_legend
  expect_equal(legend[[length(legend)]]$label, "Missing")
  expect_match(result$text, "3 without a sex are in Overall only.", fixed = TRUE)
})

test_that("hl_profile() refuses what it cannot draw, saying what to pass", {
  hl_use(brand = FALSE)
  expect_error(hl_profile(profile_study(), by = "age"), "by 'age' holds numbers")
  expect_error(hl_profile(profile_study(), by = "ward"), "by 'ward' is not a column")
  data <- profile_operations()
  data$surgery_date[4] <- "soon"
  expect_error(hl_profile(profile_study(data), dates = "surgery_date"), "'surgery_date' has 'soon'")
  expect_null(hl_profile(profile_study(variables = character()))$figure)
})

test_that("tiles follow the width and long periods count by quarter", {
  hl_use(brand = FALSE)
  expect_equal(hl_profile(profile_study(), size = "single")$figure@meta$hairline_rows$columns, 1)
  expect_equal(hl_profile(profile_study(), size = "onehalf")$figure@meta$hairline_rows$columns, 2)
  data <- profile_operations()
  data$surgery_date <- format(seq(as.Date("2015-01-01"), by = "month", length.out = 120))
  quarter <- hl_profile(profile_study(data), dates = "surgery_date")$figure@meta$hairline_rows$plots[[6]]
  expect_equal(quarter@meta$hairline_headers[[1]]$qualifier, "per quarter")
})

test_that("histogram bins are round, nearest on a log scale, and hold every value once", {
  expect_equal(round_bin_width(5.4, TRUE), 5)
  expect_equal(round_bin_width(3.4, FALSE), 2.5)
  expect_equal(round_bin_width(2.8, TRUE), 2)
  expect_equal(round_bin_width(0.3, TRUE), 1)
  days <- c(1, 1, 2, 4, 4, 4, 9)
  edges <- bin_edges(days, TRUE)
  expect_equal(edges[1], 0.5)
  expect_equal(sum(counts_in(days, edges)), length(days))
  expect_equal(counts_in(days, edges)[1], 2)
})

test_that("hl_save() writes a result's figure and its table", {
  hl_use(brand = FALSE)
  folder <- withr::local_tempdir()
  study <- suppressWarnings(hl_study(data.frame(age = c(61, 72, 55, 48)), units = c(age = "years")))
  paths <- hl_save(hl_profile(study), file.path(folder, "out", "cohort"), formats = "png", dpi = 150)
  expect_equal(basename(paths), c("cohort.png", "cohort.csv"))
  expect_equal(unlist(utils::read.csv(paths[2], colClasses = "character")[1, ]),
               c(Characteristic = "n", Overall = "4"))
})

test_that("a result shows in R Markdown as its figure, sentence and table", {
  skip_if_not_installed("knitr")
  hl_use(brand = FALSE)
  study <- suppressWarnings(hl_study(data.frame(age = c(61, 72, 55, 48)), units = c(age = "years")))
  shown <- knitr::knit_print(hl_profile(study))
  expect_s3_class(shown, "knit_asis")
  expect_match(shown, "4 participants.", fixed = TRUE)
  expect_match(shown, "Characteristic", fixed = TRUE)
})
