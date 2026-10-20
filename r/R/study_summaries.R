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

study_stat_keys <- list(median_iqr = c("median", "q1", "q3"), mean_sd = c("mean", "sd"), range = c("min", "max"),
                        n_missing = character())

# The unrounded quantities behind the statistics: n and missing, then each statistic's own (NA without values).
summary_numbers <- function(values, stats, missing) {
  found <- list(n = length(values), missing = as.integer(missing))
  for (stat in stats) {
    found[study_stat_keys[[stat]]] <- NA_real_
    if (!length(values)) next
    if (stat == "median_iqr") {
      found[c("q1", "median", "q3")] <- as.list(density_quantiles(values, c(0.25, 0.5, 0.75)))
    } else if (stat == "mean_sd") {
      found$mean <- mean(values)
      found$sd <- if (length(values) > 1) stats::sd(values) else 0
    } else if (stat == "range") {
      found[c("min", "max")] <- list(min(values), max(values))
    }
  }
  found
}

# One statistic as text from summary_numbers(); `whole` (the variable holds whole numbers) gives means one more
# decimal.
summary_text <- function(found, stat, digits, whole = FALSE) {
  if (stat == "n_missing") return(hl_format_number(found$missing, 0))
  if (!found$n) return(study_empty)
  # Snap away float noise first: R and numpy reach the same quantile by different arithmetic.
  number <- function(value) {
    hl_format_number(round(value, study_snap_digits), quantile_places(value, digits, whole))
  }
  if (stat == "median_iqr") {
    return(sprintf("%s (%s%s%s)", number(found$median), number(found$q1), study_empty, number(found$q3)))
  }
  if (stat == "mean_sd") {
    places <- digits + if (whole) 1 else 0
    return(sprintf("%s (%s)", study_mean_text(found$mean, digits, whole),
                   hl_format_number(round(found$sd, study_snap_digits), places)))
  }
  paste0(number(found$min), study_empty, number(found$max))
}

count_share <- function(count, total) {
  share <- if (total) hl_format_percent(count / total, hl_tokens()$study$percent_digits) else study_empty
  sprintf("%s (%s)", hl_format_number(count, 0), share)
}

listed_text <- function(items) {
  if (length(items) == 1) items else paste(paste(items[-length(items)], collapse = ", "), "and", items[length(items)])
}

share_of <- function(count, total) if (total) count / total else NA_real_

# The mean, with one more decimal when the variable holds whole numbers.
study_mean_text <- function(mean, digits, whole) {
  if (is.na(mean)) return(study_empty)
  hl_format_number(round(mean, study_snap_digits), digits + if (whole) 1 else 0)
}

study_missing_nouns <- c(variable = "a value", group = "a group", date = "a date")

# " 39 of 40 participants; 1 without a value was left out." from a result's rows, for the `roles` whose missing rows
# left the analysis; empty when none did.
left_out_text <- function(rows, unit, roles = c("variable", "group", "date")) {
  counts <- unlist(rows$missing[intersect(names(rows$missing), roles)])
  counts <- counts[counts > 0]
  if (!length(counts)) return("")
  parts <- paste(vapply(counts, hl_format_number, character(1), digits = 0), "without",
                 study_missing_nouns[names(counts)])
  sprintf(" %s of %s %s; %s %s left out.", hl_format_number(rows$analysed, 0), hl_format_number(rows$total, 0), unit,
          listed_text(parts), if (sum(counts) == 1) "was" else "were")
}

# " 1 without a group is counted in Overall only."; empty when every row has a group.
overall_only_text <- function(rows) {
  count <- rows$missing$group %||% 0
  if (!count) return("")
  sprintf(" %s without a group %s counted in Overall only.", hl_format_number(count, 0),
          if (count == 1) "is" else "are")
}
