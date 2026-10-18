study_fixture <- function() read_fixture("study.json")

fixture_frame <- function(columns) {
  as.data.frame(lapply(columns, function(values) {
    vapply(values, function(value) if (is.null(value)) NA else value,
           if (is.character(values[[1]])) character(1) else numeric(1))
  }), stringsAsFactors = FALSE)
}

fixture_study <- function(fixture) {
  data <- fixture_frame(fixture$cohort)
  suppressWarnings(hl_study(data, group = "arm", time = "months", event = "died", id = "id",
                            variables = c("age", "sex", "sofa", "score"),
                            units = c(age = "years", months = "months")))
}

expect_result <- function(result, case) {
  expect_equal(names(result$table), unlist(case$columns))
  expect_equal(unname(as.matrix(result$table)), do.call(rbind, lapply(case$rows, unlist)))
  expect_equal(result$values, case$values)
  expect_equal(result$text, case$text)
}

test_that("study checks match the shared fixture", {
  hl_use(brand = FALSE)
  fixture <- study_fixture()
  study <- fixture_study(fixture)
  expect_equal(lapply(study$checks, function(finding) {
    finding$rows <- as.list(finding$rows)
    finding
  }), lapply(fixture$checks, function(finding) finding[c("level", "column", "problem", "rows", "fix")]))
  broken <- fixture_frame(fixture$cohort)
  broken$died <- unlist(fixture$broken_event)
  expect_warning(failing <- hl_study(broken, group = "arm", time = "months", event = "died", variables = "age"),
                 "1 errors")
  expect_equal(failing$checks[[1]]$problem, fixture$broken_checks[[1]]$problem)
  expect_error(hl_survival(failing), "survival: fix these first")
})

test_that("study endpoints match the shared fixture", {
  hl_use(brand = FALSE)
  fixture <- study_fixture()
  study <- fixture_study(fixture)
  expect_result(hl_describe(study, c("median_iqr", "mean_sd", "range", "n_missing")), fixture$describe)
  expect_result(hl_compare(study, "sofa"), fixture$compare_numeric)
  expect_result(hl_compare(study, "sex"), fixture$compare_categorical)
  expect_result(hl_distribution(study, "age", c("median_iqr", "mean_sd")), fixture$distribution)
  expect_result(hl_survival(study), fixture$survival)
  effects <- fixture_frame(fixture$effects_table)
  expect_result(hl_effects(study, effects, measure = "OR"), fixture$effects)
  three <- suppressWarnings(hl_study(fixture_frame(fixture$three), group = "arm", variables = "lactate",
                                     units = c(lactate = "mmol/l")))
  expect_result(hl_compare(three, "lactate"), fixture$compare_three)
})

test_that("over_time matches the shared fixture and refuses dates it cannot read", {
  hl_use(brand = FALSE)
  fixture <- study_fixture()
  daily <- suppressWarnings(hl_study(fixture_frame(fixture$daily), group = "unit", variables = "occupied",
                                     units = c(occupied = "beds")))
  expect_result(hl_over_time(daily, "date", "occupied"), fixture$over_time)
  broken <- fixture_frame(fixture$daily)
  broken$date <- "next week"
  broken_study <- suppressWarnings(hl_study(broken, group = "unit", variables = "occupied"))
  expect_error(hl_over_time(broken_study, "date", "occupied"), "not an ISO date")
})

test_that("a survfit gives the same survival result as the raw rows", {
  skip_if_not_installed("survival")
  hl_use(brand = FALSE)
  fixture <- study_fixture()
  study <- fixture_study(fixture)
  data <- fixture_frame(fixture$cohort)
  fit <- survival::survfit(survival::Surv(months, died) ~ arm, data = data)
  from_fit <- hl_survival(study, fit)
  from_rows <- hl_survival(study)
  expect_equal(from_fit$table, from_rows$table)
  expect_equal(from_fit$values, from_rows$values)
  expect_equal(from_fit$text, from_rows$text)
})

test_that("a study without roles is accepted, as in Python", {
  visits <- data.frame(day = 1:30, lactate = round(2 + sin(1:30 / 5), 1))
  study <- hl_study(visits, units = c(day = "days", lactate = "mmol/l"))
  expect_equal(study$variables, c("day", "lactate"))
  expect_match(hl_over_time(study, "day", "lactate", window = 7)$text, "^Lactate")
})
