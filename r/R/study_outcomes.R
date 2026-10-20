# hl_survival() and hl_effects(): events over follow-up, and estimates from a model or a results table.

study_follow_up_rows <- function(study) {
  data <- study$data
  data[[study$roles$time]] <- study_as_number(data[[study$roles$time]])
  data[[study$roles$event]] <- as.integer(study_as_number(data[[study$roles$event]]))
  group <- study$roles$group
  if (is.null(group)) {
    data[[study_group_column]] <- rep("Overall", nrow(data))
    return(data)
  }
  data <- data[!study_is_missing(data[[group]]), , drop = FALSE]
  data[[study_group_column]] <- level_text(data[[group]])
  data
}

# Per group n, events and the median (NA when not reached), and the table rows formatted from them.
survival_rows <- function(estimates) {
  digits <- median_digits(lapply(estimates, `[[`, "table"))
  found <- lapply(estimates, function(estimate) {
    median <- km_median(estimate$table)
    list(n = estimate$total, events = sum(estimate$table$events), median = if (is.null(median)) NA_real_ else median)
  })
  names(found) <- vapply(estimates, function(estimate) if (nzchar(estimate$name)) estimate$name else "Overall",
                         character(1))
  rows <- lapply(names(found), function(name) {
    group <- found[[name]]
    c(name, hl_format_number(group$n, 0), hl_format_number(group$events, 0),
      if (is.na(group$median)) "not reached" else hl_format_number(group$median, digits))
  })
  list(rows = rows, numbers = found)
}

# Rows in the study, analysed, and missing a group; time and event cannot be missing (study checks block it).
study_follow_up_counts <- function(study) {
  group <- study$roles$group
  missing <- if (is.null(group)) stats::setNames(list(), character()) else
    list(group = sum(study_is_missing(study$data[[group]])))
  list(total = nrow(study$data), analysed = nrow(study$data) - sum(unlist(missing)), missing = missing)
}

# The log-rank test over the groups shown; p is NA when no event makes it undefined.
study_logrank <- function(data, time, event) {
  found <- logrank_test(data[[time]], data[[event]], data[[study_group_column]])
  list(method = "Log-rank", statistic = found$chisq, df = found$df, p = found$p)
}

survival_estimates <- function(study, data, fit) {
  if (is.null(fit)) {
    names <- Filter(function(name) any(data[[study_group_column]] == name),
                    if (length(study$groups)) study$groups else "Overall")
    return(lapply(names, function(name) {
      rows <- data[data[[study_group_column]] == name, , drop = FALSE]
      list(name = name, total = nrow(rows), table = km_estimate(rows[[study$roles$time]], rows[[study$roles$event]]))
    }))
  }
  if (!inherits(fit, "survfit")) stop("hairline: survival: fit must be a survival::survfit", call. = FALSE)
  estimates <- km_from_fit(fit)
  names <- vapply(estimates, `[[`, character(1), "name")
  if (length(study$groups) && all(names %in% study$groups)) estimates <- estimates[order(match(names, study$groups))]
  estimates
}

survival_text <- function(study, rows, grouped, test) {
  time <- study$roles$time
  measured <- if (is.null(time)) "survival time" else tolower(study_label(study, time))
  unit <- if (is.null(time)) NULL else study_measure(study, time)
  medians <- if (grouped) listed_text(vapply(rows, function(row) paste(row[1], row[4]), character(1))) else rows[[1]][4]
  paste0("Median ", measured, if (!is.null(unit)) sprintf(" (%s)", unit), ": ", medians,
         if (!is.null(test)) sprintf(" (log-rank %s).", test) else ".")
}

#' Survival by group
#'
#' Kaplan–Meier curves with the log-rank test; the table gives n, events and
#' the median per group. A fit already made (`survival::survfit`) can be
#' passed as `fit`; it keeps its own intervals, and the log-rank test comes
#' from the study's own time, event and group columns when they are set.
#'
#' @param study A study from [hl_study()].
#' @param fit Optional `survival::survfit`.
#' @return A `hairline_result`.
#' @examples
#' set.seed(1)
#' cohort <- data.frame(arm = rep(c("Standard care", "Early mobilisation"), each = 40),
#'                      age = round(stats::rnorm(80, 64, 12)),
#'                      sex = sample(c("Female", "Male"), 80, TRUE),
#'                      months = round(stats::rexp(80, 0.05), 1), died = stats::rbinom(80, 1, 0.4))
#' study <- hl_study(cohort, group = "arm", time = "months", event = "died",
#'                   units = c(age = "years", months = "months"))
#' hl_survival(study)$values
#' @export
hl_survival <- function(study, fit = NULL) {
  time <- study$roles$time
  event <- study$roles$event
  has_data <- !is.null(time) && !is.null(event)
  if (is.null(fit) && !has_data) {
    stop("hairline: survival needs time and event; set time = and event = in hl_study(), or pass fit =",
         call. = FALSE)
  }
  if (has_data) study_require(study, c(time, event, study$roles$group), "survival")
  data <- if (has_data) study_follow_up_rows(study) else NULL
  estimated <- survival_rows(survival_estimates(study, data, fit))
  rows <- estimated$rows
  grouped <- length(rows) > 1
  names <- names(estimated$numbers)
  test <- if (grouped && has_data && !is.null(study$roles$group)) {
    study_logrank(if (is.null(fit)) data[data[[study_group_column]] %in% names, , drop = FALSE] else data, time, event)
  }
  p <- if (is.null(test) || is.na(test$p)) NULL else format_p(test$p)
  values <- c(stats::setNames(lapply(rows, `[[`, 4), names), if (!is.null(p)) list(p = p))
  title <- if (grouped && !is.null(study$roles$group)) paste("Survival by", gsub("_", " ", study$roles$group)) else
    "Survival"
  x_title <- if (is.null(time)) "Time" else study_label_unit(study, time)
  key <- if (is.null(p)) character() else c(`Log-rank` = p)
  figure <- if (is.null(fit)) {
    hl_kaplan_meier(data, time, event, by = if (!is.null(study$roles$group)) study_group_column, order = names,
                    title = title, x_title = x_title, test = FALSE, stats = key)
  } else {
    hl_kaplan_meier(fit, title = title, x_title = x_title, stats = key)
  }
  table <- as.data.frame(do.call(rbind, rows), stringsAsFactors = FALSE)
  names(table) <- c("Group", "n", "Events", "Median")
  found <- c(if (has_data) list(rows = study_follow_up_counts(study)), list(groups = estimated$numbers),
             if (!is.null(test)) list(test = test))
  text <- paste0(survival_text(study, rows, grouped, p), if (has_data) left_out_text(found$rows, study$unit))
  study_result(figure, table, values, text, found)
}

study_effect_rows <- function(model_or_table, study_column, estimate, low, high, exponentiate) {
  if (inherits(model_or_table, c("lm", "coxph"))) return(forest_from_model(model_or_table, exponentiate))
  check_columns(model_or_table, c(study_column, estimate, low, high))
  list(ratio = isTRUE(exponentiate),
       table = data.frame(term = as.character(model_or_table[[study_column]]), estimate = model_or_table[[estimate]],
                          low = model_or_table[[low]], high = model_or_table[[high]]))
}

# Reference levels of treatment-coded factors in a fitted model: the first level under contr.treatment.
model_references <- function(model) {
  treated <- Filter(function(name) identical(model$contrasts[[name]], "contr.treatment"), names(model$xlevels))
  stats::setNames(lapply(treated, function(name) model$xlevels[[name]][1]), as.character(treated))
}

#' Effects with 95 % intervals
#'
#' From a fitted `lm`, `glm` or `coxph` model, or a table with estimate and
#' interval columns; terms that are study columns take their labels.
#'
#' @param study A study from [hl_study()].
#' @param model_or_table A fitted model or a data frame.
#' @param measure Prefix for the values and text, e.g. `"OR"`.
#' @param study_column,estimate,low,high Columns of a table.
#' @param exponentiate Exponentiate model terms; default for `glm` and `coxph`.
#' @param digits Decimals of the estimates.
#' @param ... Passed to [hl_forest()].
#' @return A `hairline_result`.
#' @examples
#' set.seed(1)
#' cohort <- data.frame(arm = rep(c("Standard care", "Early mobilisation"), each = 40),
#'                      age = round(stats::rnorm(80, 64, 12)),
#'                      sex = sample(c("Female", "Male"), 80, TRUE),
#'                      months = round(stats::rexp(80, 0.05), 1), died = stats::rbinom(80, 1, 0.4))
#' study <- hl_study(cohort, group = "arm", time = "months", event = "died",
#'                   units = c(age = "years", months = "months"))
#' model <- stats::glm(died ~ age + sex, family = stats::binomial, data = cohort)
#' hl_effects(study, model, "OR")$values
#' @export
hl_effects <- function(study, model_or_table, measure = NULL, study_column = "study", estimate = "estimate",
                       low = "low", high = "high", exponentiate = NULL, digits = 2, ...) {
  fit <- study_effect_rows(model_or_table, study_column, estimate, low, high, exponentiate)
  rows <- fit$table
  terms <- vapply(rows$term, function(term) if (term %in% names(study$data)) study_label(study, term) else term,
                  character(1), USE.NAMES = FALSE)
  prefix <- if (is.null(measure)) "" else paste0(measure, " ")
  estimates <- lapply(seq_len(nrow(rows)), function(index) {
    list(estimate = rows$estimate[index], low = rows$low[index], high = rows$high[index])
  })
  texts <- paste0(prefix, vapply(estimates, function(item) {
    hl_format_interval(item$estimate, item$low, item$high, digits = digits)
  }, character(1)))
  shown <- data.frame(study = terms, estimate = rows$estimate, low = rows$low, high = rows$high)
  ratio <- fit$ratio || (!is.null(measure) && measure %in% hl_tokens()$study$ratio_measures)
  figure <- hl_forest(shown, ratio = ratio, digits = digits, ...)
  table <- data.frame(Term = terms, `Estimate [95 % CI]` = texts, check.names = FALSE, stringsAsFactors = FALSE)
  modelled <- inherits(model_or_table, c("lm", "coxph"))
  found <- list(scale = if (ratio) "ratio" else "difference",
                reference = if (modelled) model_references(model_or_table) else stats::setNames(list(), character()),
                terms = stats::setNames(estimates, terms))
  study_result(figure, table, stats::setNames(as.list(texts), terms),
               paste0(paste(terms, texts, collapse = "; "), "."), found)
}
