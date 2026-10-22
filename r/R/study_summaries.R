# Formatted summaries for study tables and values, mirroring the Python package.

study_stat_labels <- c(median_iqr = "median (IQR)", mean_sd = "mean (SD)", range = "range", n_missing = "missing")
study_empty <- "\u2013"

check_study_stats <- function(stats) {
  if (!length(stats)) {
    stop(sprintf("hairline: study: stats is empty; use one or more of %s",
                 paste(names(study_stat_labels), collapse = ", ")), call. = FALSE)
  }
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
      found$sd <- if (length(values) > 1) stats::sd(values) else NA_real_  # undefined for one value
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
    hl_format_number(snap_noise(value), quantile_places(value, digits, whole))
  }
  if (stat == "median_iqr") {
    return(sprintf("%s (%s%s%s)", number(found$median), number(found$q1), study_empty, number(found$q3)))
  }
  if (stat == "mean_sd") {
    places <- digits + if (whole) 1 else 0
    return(sprintf("%s (%s)", study_mean_text(found$mean, digits, whole),
                   hl_format_number(snap_noise(found$sd), places)))
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
  hl_format_number(snap_noise(mean), digits + if (whole) 1 else 0)
}

study_missing_nouns <- c(variable = "a value", group = "a group", date = "a date")

study_other_groups <- "in groups not named in order"

# " 39 of 40 participants; 1 without a value was left out." from a result's rows; empty when none were. With
# `in_overall`, rows without a group or in other groups are not left out (they count in Overall).
# What a row is, c(singular, plural): a pair as given, or one plural noun whose singular drops a final s ("patients":
# "1 patient", "2 patients").
unit_nouns <- function(unit) {
  if (is.character(unit) && length(unit) == 2 && all(!is.na(unit) & nzchar(unit))) return(unit)
  if (is.character(unit) && length(unit) == 1 && !is.na(unit) && nzchar(unit)) {
    return(c(if (grepl("[^s]s$", unit)) sub("s$", "", unit) else unit, unit))
  }
  stop(sprintf(paste("hairline: study: unit must be a plural noun (\"patients\") or a singular and plural pair",
                     "(c(\"mouse\", \"mice\")); got %s"), paste(format(unit), collapse = ", ")), call. = FALSE)
}

left_out_text <- function(rows, nouns, in_overall = FALSE) {
  roles <- setdiff(names(rows$missing), if (in_overall) "group")
  counts <- c(vapply(roles, function(role) rows$missing[[role]], numeric(1), USE.NAMES = FALSE),
              if (in_overall) 0 else rows$other_groups %||% 0)
  lead <- sprintf(" %s of %s;", hl_format_number(rows$analysed, 0), counted_text(rows$total, nouns))
  parts_text(counts, c(paste("without", study_missing_nouns[roles]), study_other_groups), lead, c("was", "were"),
             "left out")
}

# " 1 without a group is counted in Overall only."; empty when every row is in a group of the study.
overall_only_text <- function(rows) {
  parts_text(c(rows$missing$group %||% 0, rows$other_groups %||% 0), c("without a group", study_other_groups), "",
             c("is", "are"), "counted in Overall only")
}

# "<lead> 2 without a value and 1 without a group were <tail>." over the nonzero counts; empty without any.
parts_text <- function(counts, labels, lead, verbs, tail) {
  shown <- counts > 0
  if (!any(shown)) return("")
  verb <- if (sum(counts[shown]) == 1) verbs[1] else verbs[2]
  parts <- paste(vapply(counts[shown], hl_format_number, character(1), digits = 0), labels[shown])
  sprintf("%s %s %s %s.", lead, listed_text(parts), verb, tail)
}
