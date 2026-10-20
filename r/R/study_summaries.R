# Formatted summaries for study tables and values, mirroring the Python package.

study_stat_labels <- c(median_iqr = "median (IQR)", mean_sd = "mean (SD)", range = "range", n_missing = "missing")
study_empty <- "\u2013"
study_snap_digits <- 10

check_study_stats <- function(stats) {
  unknown <- setdiff(stats, names(study_stat_labels))
  if (length(unknown)) {
    stop(sprintf("hairline: study: unknown statistic '%s'; use one of %s", unknown[1],
                 paste(names(study_stat_labels), collapse = ", ")), call. = FALSE)
  }
}

study_digits <- function(values) auto_digits(values)

# One statistic as text; `whole` (the variable holds whole numbers) gives means one more decimal.
numeric_summary <- function(values, stat, digits, missing, whole = FALSE) {
  if (stat == "n_missing") return(hl_format_number(missing, 0))
  if (!length(values)) return(study_empty)
  # Snap away float noise first: R and numpy reach the same quantile by different arithmetic.
  number <- function(value) {
    hl_format_number(round(value, study_snap_digits), quantile_places(value, digits, whole))
  }
  if (stat == "median_iqr") {
    limits <- density_quantiles(values, c(0.25, 0.5, 0.75))
    return(sprintf("%s (%s%s%s)", number(limits[2]), number(limits[1]), study_empty, number(limits[3])))
  }
  if (stat == "mean_sd") {
    places <- digits + if (whole) 1 else 0
    spread <- if (length(values) > 1) stats::sd(values) else 0
    return(sprintf("%s (%s)", study_mean_text(values, digits, whole),
                   hl_format_number(round(spread, study_snap_digits), places)))
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

# The mean, with one more decimal when the variable holds whole numbers.
study_mean_text <- function(values, digits, whole) {
  if (!length(values)) return(study_empty)
  hl_format_number(round(mean(values), study_snap_digits), digits + if (whole) 1 else 0)
}
