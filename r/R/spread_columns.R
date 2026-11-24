# Columns beside spread rows: other measures of each group, written in the numbers column under a heading, not
# drawn. As the Python package's charts/spread_columns.py.

spread_centres <- c("median", "mean")
spread_intervals <- c("iqr", "sd", "ci", "range")

# The columns to write, each with its label: one name, several, or c(column = "label"); numbers only.
spread_checked_columns <- function(data, columns, chart) {
  if (is.null(columns)) return(character())
  named <- if (is.null(names(columns))) stats::setNames(vapply(columns, humanise, ""), columns) else
    stats::setNames(as.character(columns), names(columns))
  check_columns(data, names(named))
  check_numeric(data, names(named), chart)
  named
}

# What each written column shows, taken from the chart's own `stats`: its first centre (median unless the mean is
# asked for) and its first interval, if any.
spread_column_measures <- function(stats) {
  centre <- stats[stats %in% spread_centres][1]
  interval <- stats[stats %in% spread_intervals][1]
  list(centre = if (is.na(centre)) "median" else centre, interval = if (is.na(interval)) NULL else interval)
}

# Each column's formatters, from all its values, so every row of a column has the same decimals.
spread_column_numbers <- function(data, columns) {
  lapply(stats::setNames(names(columns), names(columns)), function(column) {
    values <- as.numeric(data[[column]])
    measure_numbers(values[!is.na(values)], FALSE, NULL)
  })
}

# A (label, value) pair per column for group `name`: 'Age', '61.4 (53-73)'; a dash without values.
spread_column_pairs <- function(data, group, name, columns, measures, numbers) {
  rows <- !is.na(data[[group]]) & as.character(data[[group]]) == name
  lapply(names(columns), function(column) {
    values <- as.numeric(data[[column]][rows])
    values <- values[!is.na(values)]
    if (!length(values)) return(c(columns[[column]], missing_text))
    found <- summary_values(values, FALSE)
    text <- stat_text(measures$centre, found, numbers[[column]], values)
    if (!is.null(measures$interval)) {
      text <- paste0(text, " (", stat_text(measures$interval, found, numbers[[column]], values), ")")
    }
    c(columns[[column]], text)
  })
}

# The written columns right after the `stats` key numbers, before a mark: every row then has them at the same
# positions, under their headings, whether or not it has a mark.
spread_with_columns <- function(pairs, stats, columns) {
  c(utils::head(pairs, stats), columns, if (length(pairs) > stats) pairs[-seq_len(stats)])
}

# The caption's account of the written columns: 'Age (years), Stay (days): Median (IQR).'
spread_columns_note <- function(columns, measures) {
  if (!length(columns)) return(NULL)
  shown <- paste0(stat_label(measures$centre),
                  if (!is.null(measures$interval)) paste0(" (", stat_label(measures$interval), ")") else "")
  paste0(listed(unname(columns)), ": ", shown, ".")
}
