# Formatted summaries for study tables and values, mirroring the Python package.

study_stat_labels <- c(median_iqr = "median (IQR)", mean_sd = "mean (SD)", range = "range", n_missing = "missing")
study_empty <- "–"
study_snap_digits <- 10

check_study_stats <- function(stats) {
  unknown <- setdiff(stats, names(study_stat_labels))
  if (length(unknown)) {
    stop(sprintf("hairline: study: unknown statistic '%s'; use one of %s", unknown[1],
                 paste(names(study_stat_labels), collapse = ", ")), call. = FALSE)
  }
}

study_digits <- function(values) {
  magnitude <- if (length(values)) stats::median(abs(values)) else 0
  steps <- hl_tokens()$study$digit_steps
  for (index in seq_len(nrow(steps))) if (magnitude >= steps$min[index]) return(steps$digits[index])
  steps$digits[nrow(steps)]
}

numeric_summary <- function(values, stat, digits, missing) {
  if (stat == "n_missing") return(hl_format_number(missing, 0))
  if (!length(values)) return(study_empty)
  # Snap away float noise first: R and numpy reach the same quantile by different arithmetic.
  number <- function(value) hl_format_number(round(value, study_snap_digits), digits)
  if (stat == "median_iqr") {
    limits <- density_quantiles(values, c(0.25, 0.5, 0.75))
    return(sprintf("%s (%s%s%s)", number(limits[2]), number(limits[1]), study_empty, number(limits[3])))
  }
  if (stat == "mean_sd") {
    return(sprintf("%s (%s)", number(mean(values)), number(if (length(values) > 1) stats::sd(values) else 0)))
  }
  paste0(number(min(values)), study_empty, number(max(values)))
}

count_share <- function(count, total) {
  share <- if (total) hl_format_percent(count / total, hl_tokens()$study$percent_digits) else study_empty
  sprintf("%s (%s)", hl_format_number(count, 0), share)
}

listed_text <- function(items) {
  if (length(items) == 1) items else paste(paste(items[-length(items)], collapse = ", "), "and", items[length(items)])
}
