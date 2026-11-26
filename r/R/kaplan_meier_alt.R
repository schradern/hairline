# The description of Kaplan–Meier curves for their alt text: each group's median as the panel header writes it, or
# where the curve stays above half, the share still without the event at its last time; and the log-rank p where the
# chart shows one, labelled as the panel header labels it. Mirrors the Python package's charts/kaplan_meier_alt.py.

# A curve's median, or "not reached (62% at 24)" with the survival at its last time. As Python's median_part().
km_alt_median <- function(table, digits, time_digits) {
  median <- km_median(table)
  if (!is.null(median)) return(hl_format_number(median, digits))
  last <- nrow(table)
  word("km_not_reached", share = hl_format_percent(table$survival[last], digits = 0),
       time = hl_format_number(table$time[last], time_digits))
}

# "Kaplan–Meier curve. Median: ICU 9.1; Ward not reached (62% at 24). Log-rank: p = 0.003." Groups are named only
# where the chart has several; the p is the log-rank one among the panel header's numbers, with its label. As
# Python's kaplan_meier_description().
kaplan_meier_description <- function(estimates, grouped, stats) {
  tables <- lapply(estimates, `[[`, "table")
  digits <- median_digits(tables)
  times <- unlist(lapply(tables, `[[`, "time"))
  time_digits <- auto_digits(times[times > 0])
  medians <- vapply(estimates, function(estimate) {
    found <- km_alt_median(estimate$table, digits, time_digits)
    if (grouped) paste(estimate$name, found) else found
  }, character(1))
  tests <- stats[startsWith(tolower(names(stats) %||% rep("", length(stats))), "log-rank")]
  findings <- c(word("km_medians", medians = paste(medians, collapse = "; ")),
                if (length(tests)) word("km_test", label = names(tests)[1], value = tests[[1]]))
  alt_described("kind_kaplan_meier", paste(findings, collapse = " "))
}
