# Checks a study runs when it is created, mirroring the Python package; they report, they never change the data.

study_finding <- function(level, column, problem, rows, fix) {
  list(level = level, column = column, problem = problem, rows = as.integer(rows), fix = fix)
}

format_finding <- function(finding) {
  rows <- if (length(finding$rows)) sprintf(" (rows %s)", paste(finding$rows, collapse = ", ")) else ""
  sprintf("%s: %s: %s%s. Fix: %s.", finding$level, finding$column, finding$problem, rows, finding$fix)
}

count_text <- function(count) hl_format_number(count, 0)

missing_value_findings <- function(data, column, limit) {
  mask <- study_is_missing(data[[column]])
  if (!any(mask)) return(list())
  problem <- sprintf("%s missing (%s)", count_text(sum(mask)), hl_format_percent(mean(mask), 1))
  list(study_finding("warning", column, problem, row_numbers(mask, limit),
                     "endpoints leave these rows out for this column"))
}

spelling_findings <- function(data, column, limit) {
  values <- data[[column]]
  if (!is_text_column(values)) return(list())
  texts <- level_text(values)
  present <- texts[!study_is_missing(values)]
  keys <- tolower(trimws(present))
  variants <- lapply(split(present, factor(keys, levels = unique(keys))), unique)
  clashes <- Filter(function(spelled) length(spelled) > 1, variants)
  if (!length(clashes)) return(list())
  listed <- paste(vapply(clashes, function(spelled) paste0("'", spelled, "'", collapse = " / "), character(1)),
                  collapse = "; ")
  first <- vapply(variants, `[[`, character(1), 1)
  mask <- !study_is_missing(values) & texts != first[tolower(trimws(texts))]
  list(study_finding("warning", column, paste("spellings that differ only in case or spaces:", listed),
                     row_numbers(mask, limit), "recode to one spelling before the study"))
}

numbers_as_text_findings <- function(data, column) {
  values <- data[[column]]
  present <- as.character(values[!study_is_missing(values)])
  if (!is_text_column(values) || !length(present)) return(list())
  share <- mean(grepl(study_number_pattern, present, perl = TRUE))
  if (share < hl_tokens()$study$numeric_text_share) return(list())
  list(study_finding("warning", column, sprintf("stored as text, but %s of the values are numbers",
                                                hl_format_percent(share, 0)),
                     integer(), "convert the column to numbers, or declare it categorical"))
}

# A numeric variable holds numbers: text that is no number ("<5") or an infinite value cannot be summarised.
numeric_value_findings <- function(data, column, limit) {
  raw <- data[[column]]
  present <- !study_is_missing(raw)
  values <- suppressWarnings(study_as_number(raw))
  checks <- list(list(bad = present & is.na(values), problem = "are not numbers",
                      fix = "correct them, or declare the column categorical"),
                 list(bad = present & !is.na(values) & is.infinite(values), problem = "are infinite",
                      fix = "correct them, or leave these rows out"))
  findings <- list()
  for (check in checks) {
    if (!any(check$bad)) next
    shown <- paste(sprintf("'%s'", unique(as.character(raw[check$bad]))), collapse = ", ")
    problem <- sprintf("%s values %s (%s)", count_text(sum(check$bad)), check$problem, shown)
    findings[[length(findings) + 1]] <- study_finding("error", column, problem, row_numbers(check$bad, limit),
                                                      check$fix)
  }
  findings
}
