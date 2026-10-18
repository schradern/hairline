# hl_over_time(): one measure over calendar time by group, mirroring the Python over_time().

study_dated_rows <- function(study, date, value) {
  if (!date %in% names(study$data)) {
    stop(sprintf("hairline: over_time: date column '%s' is not in the data; columns: %s", date,
                 paste(names(study$data), collapse = ", ")), call. = FALSE)
  }
  data <- study_present_rows(study, value)
  data <- data[!study_is_missing(data[[date]]), , drop = FALSE]
  if (is.character(data[[date]]) || is.factor(data[[date]])) {
    parsed <- as.Date(substr(as.character(data[[date]]), 1, 10), format = "%Y-%m-%d")
    if (anyNA(parsed)) {
      stop(sprintf("hairline: over_time: '%s' has '%s', which is not an ISO date (2025-01-31)", date,
                   as.character(data[[date]])[is.na(parsed)][1]), call. = FALSE)
    }
    data[[date]] <- parsed
  }
  data[[value]] <- as.numeric(data[[value]])
  data
}

#' One measure over time by group
#'
#' Small multiples per group with the raw values and a trailing mean; the
#' table gives n, mean (SD) and median (IQR) over the whole period. ISO date
#' text (2025-01-31) is read as dates.
#'
#' @param study A study from [hl_study()].
#' @param date Column with dates (or numbers on a time axis).
#' @param value Numeric column to follow.
#' @param window Observations in the trailing mean.
#' @return A `hairline_result`.
#' @examples
#' set.seed(1)
#' visits <- data.frame(day = 1:60, lactate = round(2 + sin(1:60 / 8) + stats::rnorm(60, 0, 0.3), 1))
#' study <- hl_study(visits, units = c(day = "days", lactate = "mmol/l"))
#' hl_over_time(study, "day", "lactate", window = 7)$text
#' @export
hl_over_time <- function(study, date, value, window = 7) {
  study_require(study, c(study$roles$group, value), "over_time")
  if (!identical(study$types[[value]], "numeric")) {
    stop(sprintf("hairline: over_time: '%s' is not numeric", value), call. = FALSE)
  }
  data <- study_dated_rows(study, date, value)
  every <- study_numbers(data[[value]])
  digits <- study_digits(every)
  whole <- is_whole(every)
  names <- Filter(function(name) any(data[[study_group_column]] == name),
                  if (is.null(study$roles$group)) "Overall" else study$groups)
  samples <- lapply(names, function(name) study_numbers(data[[value]][data[[study_group_column]] == name]))
  rows <- lapply(seq_along(names), function(index) {
    c(names[index], hl_format_number(length(samples[[index]]), 0),
      numeric_summary(samples[[index]], "mean_sd", digits, 0, whole),
      numeric_summary(samples[[index]], "median_iqr", digits, 0, whole))
  })
  means <- vapply(samples, study_mean_text, character(1), digits = digits, whole = whole)
  figure <- hl_timeseries(data[order(data[[date]]), , drop = FALSE], date, value,
                          by = if (!is.null(study$roles$group)) study_group_column, order = names, window = window,
                          title = paste(study_label(study, value), "over time"))
  unit <- study_measure(study, value)
  if (!is.null(unit)) figure <- figure + ggplot2::labs(y = unit)
  table <- as.data.frame(do.call(rbind, rows), stringsAsFactors = FALSE)
  names(table) <- c("Group", "n", "mean (SD)", "median (IQR)")
  text <- sprintf("%s, mean over the period: %s.", study_label_unit(study, value),
                  listed_text(paste(names, means)))
  study_result(figure, table, stats::setNames(as.list(means), names), text)
}
