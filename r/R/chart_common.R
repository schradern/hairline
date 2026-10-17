# Input checks and data preparation shared by the chart functions.

check_columns <- function(data, columns) {
  for (column in columns) {
    if (!is.null(column) && !column %in% names(data)) {
      known <- paste(names(data), collapse = ", ")
      stop(sprintf("hairline: column '%s' is not in the data; columns: %s", column, known), call. = FALSE)
    }
  }
}

fold_other <- function(labels, values, keep = 7, other = "Other") {
  if (length(labels) <= keep) return(list(labels = labels, values = values))
  kept <- sort(order(-values, seq_along(values))[seq_len(keep - 1)])
  list(labels = c(labels[kept], other), values = c(values[kept], sum(values[-kept])))
}
