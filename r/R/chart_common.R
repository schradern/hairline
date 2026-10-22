# Input checks and data preparation shared by the chart functions.

check_columns <- function(data, columns) {
  for (column in columns) {
    if (!is.null(column) && !column %in% names(data)) {
      known <- paste(names(data), collapse = ", ")
      stop(sprintf("hairline: column '%s' is not in the data; columns: %s", column, known), call. = FALSE)
    }
  }
}

# More than `keep` entries: the `keep - 1` largest stay in given order, the rest sum into `other`. An entry already
# named `other` always joins the rest, so the chart never shows two of them.
fold_other <- function(labels, values, keep = 7, other = "Other") {
  if (length(labels) <= keep) return(list(labels = labels, values = values))
  candidates <- which(labels != other)
  kept <- sort(candidates[order(-values[candidates], candidates)][seq_len(keep - 1)])
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
  data[[name]] <- rep(1, nrow(data))
  list(data = data, value = name)
}

formula_sides <- function(formula) {
  list(left = formula[[2]], right = if (length(formula) > 2) all.vars(formula[[3]]) else character())
}

# Every row names its group; a missing label would become a group called "NA" or lose its rows.
check_labels <- function(data, columns, chart) {
  for (column in columns) {
    missing <- which(is.na(data[[column]]))
    if (length(missing)) {
      stop(sprintf(paste("hairline: %s: '%s' is missing in row %d; every row needs a name there: fill it",
                         "(e.g. 'Unknown') or drop the row"), chart, column, missing[1]), call. = FALSE)
    }
  }
}

# Something to draw: at least one row with a value.
check_present <- function(data, column, chart) {
  if (!any(!is.na(data[[column]]))) {
    stop(sprintf("hairline: %s: no values to draw; '%s' is empty or missing in every row", chart, column),
         call. = FALSE)
  }
}

# Groups as text: a factor's present levels in their order, otherwise in order of first appearance.
group_names <- function(values) {
  present <- unique(as.character(values[!is.na(values)]))
  if (is.factor(values)) return(levels(values)[levels(values) %in% present])
  present
}

# The groups in `order`, which may only name groups in the data; with `complete`, the groups it leaves out follow in
# data order (flows need every node), otherwise they are left out.
ordered_names <- function(values, order, chart, column, complete = FALSE) {
  names <- group_names(values)
  if (!length(order)) return(names)
  wanted <- as.character(order)
  repeated <- unique(wanted[duplicated(wanted)])
  if (length(repeated)) {
    stop(sprintf("hairline: %s: order names '%s' more than once; each group is drawn once", chart, repeated[1]),
         call. = FALSE)
  }
  unknown <- setdiff(wanted, names)
  if (length(unknown)) {
    stop(sprintf("hairline: %s: order names '%s', which is not a group in '%s'; groups: %s", chart, unknown[1],
                 column, paste(names, collapse = ", ")), call. = FALSE)
  }
  if (complete) c(wanted, setdiff(names, wanted)) else wanted
}

# The groups a chart draws: labels checked, then `order` or the data's own order.
chart_groups <- function(data, by, order, chart) {
  if (is.null(by)) return("")
  check_labels(data, by, chart)
  ordered_names(data[[by]], order, chart, by)
}

# Rows with a value, and the node names (those in `order` first, the rest in data order). Missing names, negative
# values and flows from a node to itself are refused: a ring or a baseline cannot draw a self-flow.
flow_rows <- function(data, source, target, value, chart, order) {
  check_columns(data, c(source, target, value))
  check_labels(data, c(source, target), chart)
  check_numeric(data, value, chart)
  rows <- data[!is.na(data[[value]]), , drop = FALSE]
  negative <- which(rows[[value]] < 0)
  if (length(negative)) {
    stop(sprintf("hairline: %s: %s \u2013 %s has a negative value (%s); flows need values of zero or more", chart,
                 rows[[source]][negative[1]], rows[[target]][negative[1]], format(rows[[value]][negative[1]])),
         call. = FALSE)
  }
  selves <- which(as.character(rows[[source]]) == as.character(rows[[target]]) & rows[[value]] > 0)
  if (length(selves)) {
    stop(sprintf(paste("hairline: %s: %s \u2192 %s flows to itself; a %s diagram draws flows between different",
                       "groups, so leave those rows out"), chart, rows[[source]][selves[1]], rows[[source]][selves[1]],
                 chart), call. = FALSE)
  }
  if (!any(rows[[value]] > 0)) {
    stop(sprintf("hairline: %s: no flows above zero to draw in '%s'", chart, value), call. = FALSE)
  }
  pairs <- as.vector(rbind(as.character(data[[source]]), as.character(data[[target]])))
  list(rows = rows, names = ordered_names(pairs, order, chart, paste0(source, "' or '", target), complete = TRUE))
}

# Measurements are numbers; text or dates in a value column get a message rather than a failed calculation.
check_numeric <- function(data, columns, chart) {
  for (column in columns) {
    if (!is.numeric(data[[column]]) || inherits(data[[column]], c("Date", "POSIXt", "difftime"))) {
      stop(sprintf("hairline: %s: '%s' holds %s values; it needs numbers", chart, column, class(data[[column]])[1]),
           call. = FALSE)
    }
    check_finite(data, column, chart)
  }
}

# An infinite value has no place on an axis, in a sum or a share; missing values are left out elsewhere.
check_finite <- function(data, column, chart) {
  values <- data[[column]]
  if (!is.numeric(values) || inherits(values, c("Date", "POSIXt", "difftime"))) return(invisible())
  infinite <- which(is.infinite(values))
  if (length(infinite)) {
    stop(sprintf("hairline: %s: '%s' is infinite in row %d; correct the value or leave the row out", chart, column,
                 infinite[1]), call. = FALSE)
  }
}

# A key per combination of labels that no two different combinations share, whatever characters the labels hold:
# each label with its length in front ("1:A2:BC" for A and BC). Vectorised over rows.
combination_key <- function(...) {
  parts <- lapply(list(...), as.character)
  do.call(paste0, lapply(parts, function(part) paste0(nchar(part, type = "chars"), ":", part)))
}
