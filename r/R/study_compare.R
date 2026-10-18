# hl_distribution() and hl_compare(): one variable by group, mirroring the Python package.

study_group_column <- ".group"

study_present_rows <- function(study, variable) {
  data <- study$data[!study_is_missing(study$data[[variable]]), , drop = FALSE]
  group <- study$roles$group
  if (is.null(group)) {
    data[[study_group_column]] <- rep("Overall", nrow(data))
    return(data)
  }
  data <- data[!study_is_missing(data[[group]]), , drop = FALSE]
  data[[study_group_column]] <- level_text(data[[group]])
  data
}

numeric_test <- function(samples) {
  if (length(samples) == 2) return(c("Wilcoxon rank-sum", format_p(rank_sum_p(samples[[1]], samples[[2]]))))
  if (length(samples) > 2) return(c("Kruskal–Wallis", format_p(kruskal_p(samples))))
  NULL
}

study_by_title <- function(study, label) {
  if (is.null(study$roles$group)) label else paste(label, "by", gsub("_", " ", study$roles$group))
}

#' Distribution of one numeric variable by group
#'
#' @param study A study from [hl_study()].
#' @param variable A numeric variable.
#' @param stats Statistics as in [hl_describe()].
#' @return A `hairline_result`; the figure is a raincloud, or a ridgeline from five groups.
#' @export
hl_distribution <- function(study, variable, stats = "median_iqr") {
  check_study_stats(stats)
  study_require(study, c(study$roles$group, variable), "distribution")
  if (!identical(study$types[[variable]], "numeric")) {
    stop(sprintf("hairline: distribution: '%s' is categorical; use hl_compare() for its shares", variable),
         call. = FALSE)
  }
  digits <- study_digits(study_numbers(study$data[[variable]]))
  label <- study_label(study, variable)
  parts <- study_subsets(study)
  rows <- lapply(parts, function(part) {
    values <- part$rows[[variable]]
    c(part$name, hl_format_number(sum(!study_is_missing(values)), 0),
      vapply(stats, numeric_summary, character(1), values = study_numbers(values), digits = digits,
             missing = sum(study_is_missing(values))))
  })
  table <- as.data.frame(do.call(rbind, rows), stringsAsFactors = FALSE)
  names(table) <- c("Group", "n", unname(study_stat_labels[stats]))
  data <- study_present_rows(study, variable)
  data[[variable]] <- as.numeric(data[[variable]])
  names <- if (is.null(study$roles$group)) "Overall" else vapply(parts[-length(parts)], `[[`, character(1), "name")
  chart <- if (length(names) >= hl_tokens()$study$ridgeline_from) hl_ridgeline else hl_raincloud
  figure <- chart(data, study_group_column, variable, order = names, title = study_by_title(study, label))
  shown <- if (is.null(study$roles$group)) rows else rows[-length(rows)]
  text <- sprintf("%s, %s: %s.", label, study_stat_labels[[stats[1]]],
                  listed_text(vapply(shown, function(row) paste(row[1], row[3]), character(1))))
  study_result(figure, table, stats::setNames(lapply(rows, `[[`, 3), vapply(rows, `[[`, character(1), 1)), text)
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
#' @export
hl_compare <- function(study, variable) {
  if (is.null(study$roles$group)) stop("hairline: compare needs a group; set group = in hl_study()", call. = FALSE)
  study_require(study, c(study$roles$group, variable), "compare")
  if (identical(study$types[[variable]], "numeric")) compare_numeric(study, variable) else
    compare_categorical(study, variable)
}

compare_numeric <- function(study, variable) {
  data <- study_present_rows(study, variable)
  label <- study_label(study, variable)
  digits <- study_digits(study_numbers(data[[variable]]))
  names <- Filter(function(name) any(data[[study_group_column]] == name), study$groups)
  samples <- lapply(names, function(name) study_numbers(data[[variable]][data[[study_group_column]] == name]))
  summaries <- vapply(samples, numeric_summary, character(1), stat = "median_iqr", digits = digits, missing = 0)
  test <- numeric_test(samples)
  rows <- lapply(seq_along(names), function(index) {
    c(names[index], hl_format_number(length(samples[[index]]), 0), summaries[index])
  })
  if (!is.null(test)) rows[[length(rows) + 1]] <- c("Test", "", paste0(test[1], ", ", test[2]))
  table <- as.data.frame(do.call(rbind, rows), stringsAsFactors = FALSE)
  names(table) <- c("Group", "n", "median (IQR)")
  values <- c(stats::setNames(as.list(summaries), names), if (!is.null(test)) list(test = test[1], p = test[2]))
  pairs <- if (!is.null(test) && length(names) == 2) list(c(names, test[2])) else list()
  subtitle <- if (!is.null(test) && length(names) > 2) paste0(test[1], ", ", test[2]) else NULL
  data[[variable]] <- as.numeric(data[[variable]])
  figure <- hl_raincloud(data, study_group_column, variable, order = names, comparisons = pairs,
                         title = study_by_title(study, label), subtitle = subtitle)
  text <- paste0(label, ", median (IQR): ", listed_text(paste(names, summaries)),
                 if (!is.null(test)) sprintf(" (%s, %s).", test[1], test[2]) else ".")
  study_result(figure, table, values, text)
}

compare_categorical <- function(study, variable) {
  data <- study_present_rows(study, variable)
  label <- study_label(study, variable)
  data[[variable]] <- level_text(data[[variable]])
  names <- Filter(function(name) any(data[[study_group_column]] == name), study$groups)
  kinds <- study_levels(data[[variable]])
  counts <- t(vapply(kinds, function(kind) {
    vapply(names, function(name) sum(data[[study_group_column]] == name & data[[variable]] == kind), numeric(1))
  }, numeric(length(names))))
  if (length(names) == 1) counts <- t(counts)
  totals <- vapply(names, function(name) sum(data[[study_group_column]] == name), numeric(1))
  rows <- lapply(seq_along(kinds), function(row) {
    c(kinds[row], vapply(seq_along(names), function(column) count_share(counts[row, column], totals[column]),
                         character(1)))
  })
  test <- if (length(names) > 1 && length(kinds) > 1) c("Chi-squared", format_p(chi_square_p(counts))) else NULL
  values <- stats::setNames(lapply(seq_along(names), function(column) {
    stats::setNames(lapply(rows, function(row) row[column + 1]), kinds)
  }), names)
  if (!is.null(test)) {
    rows[[length(rows) + 1]] <- c("Test", paste0(test[1], ", ", test[2]), rep("", length(names) - 1))
    values <- c(values, list(test = test[1], p = test[2]))
  }
  table <- as.data.frame(do.call(rbind, rows), stringsAsFactors = FALSE)
  names(table) <- c(label, names)
  figure <- hl_bars(data, study_group_column, by = variable, stacked = TRUE, percent = TRUE, horizontal = TRUE,
                    order = names, title = study_by_title(study, label))
  text <- paste0(study_by_title(study, label), if (!is.null(test)) sprintf(": %s, %s.", test[1], test[2]) else ".")
  study_result(figure, table, values, text)
}
