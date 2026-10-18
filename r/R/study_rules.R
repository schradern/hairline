# Role-specific study checks: follow-up time, events, groups and ids.

time_findings <- function(data, column, limit) {
  raw <- data[[column]]
  values <- if (is.numeric(raw)) raw else suppressWarnings(as.numeric(as.character(raw)))
  values[study_is_missing(raw)] <- NA
  bad <- is.na(values) | (!is.na(values) & values < 0)
  if (!any(bad)) return(list())
  list(study_finding("error", column, sprintf("%s follow-up times are missing, negative or not numbers",
                                              count_text(sum(bad))),
                     row_numbers(bad, limit), "correct or drop these rows; times count from the start of follow-up"))
}

event_findings <- function(data, column, limit) {
  values <- data[[column]]
  valid <- if (is.logical(values)) !is.na(values) else if (is.numeric(values)) {
    !is.na(values) & values %in% c(0, 1)
  } else {
    rep(FALSE, length(values))
  }
  if (all(valid)) return(list())
  list(study_finding("error", column, sprintf("%s event values are not 0/1 (or TRUE/FALSE)", count_text(sum(!valid))),
                     row_numbers(!valid, limit), "code events as 1 (event) and 0 (censored)"))
}

group_findings <- function(data, column, groups, limit) {
  findings <- c(missing_value_findings(data, column, limit), spelling_findings(data, column, limit))
  labels <- level_text(data[[column]])
  labels[study_is_missing(data[[column]])] <- NA
  for (name in groups) {
    size <- sum(labels == name, na.rm = TRUE)
    if (size < hl_tokens()$study$small_group) {
      findings[[length(findings) + 1]] <- study_finding("warning", column,
                                                        sprintf("group '%s' has %s rows", name, count_text(size)),
                                                        integer(),
                                                        "merge it with a similar group or leave it out of comparisons")
    }
  }
  findings
}

id_findings <- function(data, column, limit) {
  missing <- study_is_missing(data[[column]])
  texts <- level_text(data[[column]])
  repeated <- !missing & duplicated(ifelse(missing, NA, texts), incomparables = NA)
  if (!any(repeated)) return(list())
  list(study_finding("warning", column, sprintf("%s rows repeat an id", count_text(sum(repeated))),
                     row_numbers(repeated, limit), "keep one row per id, or leave out the id role if rows are visits"))
}

run_study_checks <- function(data, roles, variables, groups) {
  limit <- hl_tokens()$study$example_rows
  named <- c(unlist(roles) %||% character(),
             stats::setNames(variables, rep("variable", length(variables))))
  choices <- paste("use one of:", paste(names(data), collapse = ", "))
  findings <- lapply(which(!named %in% names(data)), function(index) {
    study_finding("error", named[[index]], sprintf("not in the data (role: %s)", names(named)[index]), integer(),
                  choices)
  })
  if (!is.null(roles$time) && roles$time %in% names(data)) {
    findings <- c(findings, time_findings(data, roles$time, limit))
  }
  if (!is.null(roles$event) && roles$event %in% names(data)) {
    findings <- c(findings, event_findings(data, roles$event, limit))
  }
  if (!is.null(roles$group) && roles$group %in% names(data)) {
    findings <- c(findings, group_findings(data, roles$group, groups, limit))
  }
  if (!is.null(roles$id) && roles$id %in% names(data)) findings <- c(findings, id_findings(data, roles$id, limit))
  for (name in intersect(variables, names(data))) {
    findings <- c(findings, missing_value_findings(data, name, limit), spelling_findings(data, name, limit),
                  numbers_as_text_findings(data, name))
  }
  unname(findings)
}
