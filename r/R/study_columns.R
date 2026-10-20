# Reading study columns the same way as the Python package: missing values, numbers stored as text, level names.

study_number_pattern <- "^\\s*[-+]?([0-9]+\\.?[0-9]*|\\.[0-9]+)([eE][-+]?[0-9]+)?\\s*$"

study_is_missing <- function(values) {
  missing <- is.na(values)
  if (is.character(values) || is.factor(values)) missing <- missing | trimws(as.character(values)) == ""
  missing
}

level_text <- function(values) {
  if (is.logical(values)) return(ifelse(values, "Yes", "No"))
  if (is.numeric(values)) {
    whole <- !is.na(values) & values == round(values)
    return(ifelse(whole, sprintf("%.0f", values), as.character(values)))
  }
  as.character(values)
}

study_levels <- function(values, ordered = TRUE) {
  present <- unique(level_text(values[!study_is_missing(values)]))
  if (is.factor(values)) return(levels(values)[levels(values) %in% present])
  if (!ordered) return(present)
  if (length(present) && all(grepl(study_number_pattern, present, perl = TRUE))) {
    return(present[order(as.numeric(present))])
  }
  sort(present, method = "radix")
}

is_text_column <- function(values) !is.numeric(values) && !is.logical(values)

infer_study_type <- function(values) {
  if (inherits(values, c("Date", "POSIXt"))) return("date")
  if (is_text_column(values) || is.logical(values)) return("categorical")
  if (length(unique(values[!study_is_missing(values)])) > 2) "numeric" else "categorical"
}

# Numbers from a column; a factor gives its labels ("20"), never its level codes.
study_as_number <- function(values) if (is.factor(values)) as.numeric(as.character(values)) else as.numeric(values)

study_numbers <- function(values) study_as_number(values[!study_is_missing(values)])

row_numbers <- function(mask, limit) utils::head(which(mask), limit)
