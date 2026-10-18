# hl_survival() and hl_effects(): events over follow-up, and estimates from a model or a results table.

study_follow_up_rows <- function(study) {
  data <- study$data
  data[[study$roles$time]] <- as.numeric(data[[study$roles$time]])
  data[[study$roles$event]] <- as.integer(data[[study$roles$event]])
  group <- study$roles$group
  if (is.null(group)) {
    data[[study_group_column]] <- rep("Overall", nrow(data))
    return(data)
  }
  data <- data[!study_is_missing(data[[group]]), , drop = FALSE]
  data[[study_group_column]] <- level_text(data[[group]])
  data
}

#' Survival by group
#'
#' Kaplan–Meier curves with the log-rank test; the table gives n, events and
#' the median per group.
#'
#' @param study A study from [hl_study()] with time and event.
#' @return A `hairline_result`.
#' @export
hl_survival <- function(study) {
  time <- study$roles$time
  event <- study$roles$event
  if (is.null(time) || is.null(event)) {
    stop("hairline: survival needs time and event; set time = and event = in hl_study()", call. = FALSE)
  }
  study_require(study, c(time, event, study$roles$group), "survival")
  data <- study_follow_up_rows(study)
  names <- Filter(function(name) any(data[[study_group_column]] == name),
                  if (length(study$groups)) study$groups else "Overall")
  rows <- lapply(names, function(name) {
    subset <- data[data[[study_group_column]] == name, , drop = FALSE]
    median <- km_median(km_estimate(subset[[time]], subset[[event]]))
    c(name, hl_format_number(nrow(subset), 0), hl_format_number(sum(subset[[event]]), 0),
      if (is.null(median)) "not reached" else hl_format_number(median, 1))
  })
  test <- if (length(names) > 1) format_p(logrank_test(data[[time]], data[[event]], data[[study_group_column]])$p)
  values <- c(stats::setNames(lapply(rows, `[[`, 4), names), if (!is.null(test)) list(p = test))
  grouped <- !is.null(study$roles$group)
  title <- if (grouped) paste("Survival by", gsub("_", " ", study$roles$group)) else "Survival"
  figure <- hl_kaplan_meier(data, time, event, by = if (grouped) study_group_column, order = names, title = title,
                            x_title = study_label(study, time))
  medians <- if (grouped) listed_text(vapply(rows, function(row) paste(row[1], row[4]), character(1))) else rows[[1]][4]
  text <- paste0("Median ", tolower(study_label(study, time)), ": ", medians,
                 if (!is.null(test)) sprintf(" (log-rank %s).", test) else ".")
  table <- as.data.frame(do.call(rbind, rows), stringsAsFactors = FALSE)
  names(table) <- c("Group", "n", "Events", "Median")
  study_result(figure, table, values, text)
}

study_effect_rows <- function(model_or_table, study_column, estimate, low, high, exponentiate) {
  if (inherits(model_or_table, c("lm", "coxph"))) return(forest_from_model(model_or_table, exponentiate))
  check_columns(model_or_table, c(study_column, estimate, low, high))
  list(ratio = isTRUE(exponentiate),
       table = data.frame(term = as.character(model_or_table[[study_column]]), estimate = model_or_table[[estimate]],
                          low = model_or_table[[low]], high = model_or_table[[high]]))
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
#' @export
hl_effects <- function(study, model_or_table, measure = NULL, study_column = "study", estimate = "estimate",
                       low = "low", high = "high", exponentiate = NULL, digits = 2, ...) {
  fit <- study_effect_rows(model_or_table, study_column, estimate, low, high, exponentiate)
  rows <- fit$table
  terms <- vapply(rows$term, function(term) if (term %in% names(study$data)) study_label(study, term) else term,
                  character(1), USE.NAMES = FALSE)
  prefix <- if (is.null(measure)) "" else paste0(measure, " ")
  texts <- paste0(prefix, mapply(hl_format_interval, rows$estimate, rows$low, rows$high,
                                 MoreArgs = list(digits = digits), USE.NAMES = FALSE))
  shown <- data.frame(study = terms, estimate = rows$estimate, low = rows$low, high = rows$high)
  ratio <- fit$ratio || (!is.null(measure) && measure %in% hl_tokens()$study$ratio_measures)
  figure <- hl_forest(shown, ratio = ratio, ...)
  table <- data.frame(Term = terms, `Estimate [95 % CI]` = texts, check.names = FALSE, stringsAsFactors = FALSE)
  study_result(figure, table, stats::setNames(as.list(texts), terms),
               paste0(paste(terms, texts, collapse = "; "), "."))
}
