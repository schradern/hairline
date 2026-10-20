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

count_column <- "Count"

humanise <- function(name) {
  words <- trimws(gsub("[_.]", " ", name))
  paste0(toupper(substr(words, 1, 1)), substring(words, 2))
}

joined <- function(names) {
  names <- gsub("_", " ", names)
  if (length(names) == 1) return(names)
  paste(paste(names[-length(names)], collapse = ", "), "and", names[length(names)])
}

# Raw rows count one each when no value column is given; the count takes a name no data column has (Count, else
# Rows, else Row count, else numbered), so it never overwrites one.
with_counts <- function(data, value) {
  if (!is.null(value)) return(list(data = data, value = value))
  candidates <- c(count_column, "Rows", "Row count", paste(count_column, seq_len(ncol(data)) + 1L))
  name <- candidates[!candidates %in% names(data)][1]
  data[[name]] <- 1
  list(data = data, value = name)
}

formula_sides <- function(formula) {
  list(left = formula[[2]], right = if (length(formula) > 2) all.vars(formula[[3]]) else character())
}
