# hl_distribution() and hl_compare(): one variable by group, mirroring the Python package.

study_present_rows <- function(study, variable) {
  data <- study$data[!study_is_missing(study$data[[variable]]), , drop = FALSE]
  group <- study$roles$group
  if (is.null(group)) {
    data[[study_group_key(study)]] <- rep(study_overall(study), nrow(data))
    return(data)
  }
  data <- data[!study_is_missing(data[[group]]), , drop = FALSE]
  data[[study_group_key(study)]] <- level_text(data[[group]])
  data
}

study_require_values <- function(names, variable, endpoint) {
  if (!length(names)) {
    stop(sprintf("hairline: %s: '%s' has no values in any group of the study", endpoint, variable), call. = FALSE)
  }
}

# Per part (group, or Overall) the summary numbers of a numeric variable.
study_part_summaries <- function(parts, variable, stats) {
  stats::setNames(lapply(parts, function(part) {
    values <- part$rows[[variable]]
    summary_numbers(study_numbers(values), stats, sum(study_is_missing(values)))
  }), study_part_names(parts))
}

numeric_test <- function(samples) {
  if (length(samples) == 2) return(c(list(method = "Wilcoxon rank-sum"), rank_sum_test(samples[[1]], samples[[2]])))
  if (length(samples) > 2) return(c(list(method = "Kruskal\u2013Wallis"), kruskal_test(samples)))
  NULL
}

test_text <- function(test) paste0(test$method, ", ", format_p(test$p))

study_by_title <- function(study, label) {
  if (is.null(study$roles$group)) label else paste(label, "by", gsub("_", " ", study$roles$group))
}

#' Distribution of one numeric variable by group
#'
#' @param study A study from [hl_study()].
#' @param variable A numeric variable.
#' @param stats Statistics as in [hl_describe()].
#' @return A `hairline_result`; the figure is a raincloud, or a ridgeline from five groups.
#' @examples
#' set.seed(1)
#' cohort <- data.frame(arm = rep(c("Standard care", "Early mobilisation"), each = 40),
#'                      age = round(stats::rnorm(80, 64, 12)),
#'                      sex = sample(c("Female", "Male"), 80, TRUE),
#'                      months = round(stats::rexp(80, 0.05), 1), died = stats::rbinom(80, 1, 0.4))
#' study <- hl_study(cohort, group = "arm", time = "months", event = "died",
#'                   units = c(age = "years", months = "months"))
#' hl_distribution(study, "age", stats = c("median_iqr", "range"))$values
#' @export
hl_distribution <- function(study, variable, stats = "median_iqr") {
  check_study_stats(stats)
  kind <- study_kind(study, variable, "distribution")
  study_require(study, c(study$roles$group, variable), "distribution")
  if (!identical(kind, "numeric")) {
    stop(sprintf("hairline: distribution: '%s' is categorical; use hl_compare() for its shares", variable),
         call. = FALSE)
  }
  study_require_one_row(study, variable, "distribution")
  digits <- study_digits(study_numbers(study$data[[variable]]))
  label <- study_label_unit(study, variable)
  whole <- is_whole(study_numbers(study$data[[variable]]))
  found <- study_part_summaries(study_subsets(study), variable, stats)
  rows <- lapply(names(found), function(name) {
    c(name, hl_format_number(found[[name]]$n, 0),
      vapply(stats, summary_text, character(1), found = found[[name]], digits = digits, whole = whole))
  })
  table <- as.data.frame(do.call(rbind, rows), stringsAsFactors = FALSE)
  names(table) <- c("Group", "n", unname(study_stat_labels[stats]))
  data <- study_present_rows(study, variable)
  data[[variable]] <- study_as_number(data[[variable]])
  names <- if (is.null(study$roles$group)) study_overall(study) else names(found)[-length(found)]
  figure <- hl_spread(data, study_group_key(study), variable, order = names,
                      title = study_by_title(study, study_label(study, variable)),
                      axis_title = study_measure(study, variable))
  shown <- if (is.null(study$roles$group)) rows else rows[-length(rows)]
  counted <- study_counted_rows(study, c(list(variable = variable), study_group_role(study)), in_overall = TRUE)
  text <- paste0(sprintf("%s, %s: %s.", label, study_stat_labels[[stats[1]]],
                         listed_text(vapply(shown, function(row) paste(row[1], row[3]), character(1)))),
                 left_out_text(counted, study$unit, in_overall = TRUE), overall_only_text(counted))
  study_result(figure, table, stats::setNames(lapply(rows, `[[`, 3), vapply(rows, `[[`, character(1), 1)), text,
               list(rows = counted, groups = found))
}

#' Compare one variable between groups
#'
#' Numeric variables: median (IQR) per group with the Wilcoxon rank-sum test
#' (two groups) or Kruskal–Wallis (more), shown as a raincloud. Categorical
#' variables: n (%) per group with the chi-squared test, shown as 100 % bars.
#'
#' @param study A study from [hl_study()] with a group.
#' @param variable The variable to compare.
#' @return A `hairline_result`.
#' @examples
#' set.seed(1)
#' cohort <- data.frame(arm = rep(c("Standard care", "Early mobilisation"), each = 40),
#'                      age = round(stats::rnorm(80, 64, 12)),
#'                      sex = sample(c("Female", "Male"), 80, TRUE),
#'                      months = round(stats::rexp(80, 0.05), 1), died = stats::rbinom(80, 1, 0.4))
#' study <- hl_study(cohort, group = "arm", time = "months", event = "died",
#'                   units = c(age = "years", months = "months"))
#' hl_compare(study, "age")$text
#' hl_compare(study, "sex")$table
#' @export
hl_compare <- function(study, variable) {
  if (is.null(study$roles$group)) stop("hairline: compare needs a group; set group = in hl_study()", call. = FALSE)
  kind <- study_kind(study, variable, "compare")
  if (kind == "date") {
    stop(sprintf("hairline: compare: '%s' holds dates; follow a measure over it with hl_over_time()", variable),
         call. = FALSE)
  }
  study_require(study, c(study$roles$group, variable), "compare")
  study_require_one_row(study, variable, "compare")
  if (identical(kind, "numeric")) compare_numeric(study, variable) else compare_categorical(study, variable)
}

study_group_parts <- function(study) utils::head(study_subsets(study), -1)

compare_numeric <- function(study, variable) {
  data <- study_present_rows(study, variable)
  label <- study_label_unit(study, variable)
  digits <- study_digits(study_numbers(data[[variable]]))
  parts <- study_group_parts(study)
  found <- study_part_summaries(parts, variable, "median_iqr")
  names <- Filter(function(name) found[[name]]$n > 0, study$groups)
  study_require_values(names, variable, "compare")
  test <- numeric_test(lapply(parts[study$groups %in% names], function(part) study_numbers(part$rows[[variable]])))
  summaries <- vapply(found[names], summary_text, character(1), stat = "median_iqr", digits = digits,
                      USE.NAMES = FALSE)
  rows <- lapply(seq_along(names), function(index) {
    c(names[index], hl_format_number(found[[names[index]]]$n, 0), summaries[index])
  })
  if (!is.null(test)) rows[[length(rows) + 1]] <- c("Test", "", test_text(test))
  table <- as.data.frame(do.call(rbind, rows), stringsAsFactors = FALSE)
  names(table) <- c("Group", "n", "median (IQR)")
  values <- c(stats::setNames(as.list(summaries), names),
              if (!is.null(test)) list(test = test$method, p = format_p(test$p)))
  data[[variable]] <- study_as_number(data[[variable]])
  figure <- hl_spread(data, study_group_key(study), variable, order = names,
                      title = study_by_title(study, study_label(study, variable)),
                      subtitle = if (!is.null(test)) test_text(test), axis_title = study_measure(study, variable))
  counted <- study_counted_rows(study, c(list(variable = variable), study_group_role(study)))
  text <- paste0(label, ", median (IQR): ", listed_text(paste(names, summaries)),
                 if (!is.null(test)) sprintf(" (%s).", test_text(test)) else ".", left_out_text(counted, study$unit))
  study_result(figure, table, values, text,
               c(list(rows = counted, groups = found), if (!is.null(test)) list(test = test)))
}

compare_categorical <- function(study, variable) {
  data <- study_present_rows(study, variable)
  label <- study_label(study, variable)
  data[[variable]] <- level_text(data[[variable]])
  kinds <- study_levels(data[[variable]])
  parts <- study_group_parts(study)
  found <- stats::setNames(lapply(parts, function(part) level_numbers(part$rows[[variable]], kinds)),
                           study_part_names(parts))
  names <- Filter(function(name) found[[name]]$n > 0, study$groups)
  study_require_values(names, variable, "compare")
  counts <- matrix(unlist(lapply(found[names], `[[`, "counts")), nrow = length(kinds))
  rows <- lapply(kinds, function(kind) {
    c(kind, vapply(found[names], function(part) count_share(part$counts[[kind]], part$n), character(1),
                   USE.NAMES = FALSE))
  })
  test <- if (length(names) > 1 && length(kinds) > 1) c(list(method = "Chi-squared"), chi_square_test(counts))
  values <- stats::setNames(lapply(seq_along(names), function(column) {
    stats::setNames(lapply(rows, function(row) row[column + 1]), kinds)
  }), names)
  if (!is.null(test)) {
    rows[[length(rows) + 1]] <- c("Test", test_text(test), rep("", length(names) - 1))
    values <- c(values, list(test = test$method, p = format_p(test$p)))
  }
  table <- as.data.frame(do.call(rbind, rows), stringsAsFactors = FALSE)
  names(table) <- c(label, names)
  figure <- hl_bars(data, study_group_key(study), by = variable, stacked = TRUE, percent = TRUE, horizontal = TRUE,
                    order = names, title = study_by_title(study, label))
  counted <- study_counted_rows(study, c(list(variable = variable), study_group_role(study)))
  text <- paste0(study_by_title(study, label), if (!is.null(test)) sprintf(": %s.", test_text(test)) else ".",
                 left_out_text(counted, study$unit))
  study_result(figure, table, values, text,
               c(list(rows = counted, groups = found), if (!is.null(test)) list(test = test)))
}
