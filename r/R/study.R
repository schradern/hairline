# A study: a dataset described once, checked when it is created, mirroring hl.study().

#' Describe a dataset once for the study endpoints
#'
#' Names the column that plays each role, runs the checks and returns a study
#' for [hl_describe()], [hl_distribution()], [hl_compare()], [hl_survival()]
#' and [hl_effects()]. Checks report problems (print the study) and never
#' change the data; errors block only the endpoints that need the column.
#'
#' @param data A data frame, one row per participant.
#' @param group Column with the comparison groups.
#' @param time,event Follow-up time and event (1 = event, 0 = censored).
#' @param id Participant id, checked for duplicates.
#' @param variables Characteristics to describe; default every other column.
#' @param labels Named display names, e.g. `c(sofa = "SOFA score")`.
#' @param types Named types overriding the inference, e.g. `c(score = "categorical")`.
#' @param order Group order; default order of first appearance.
#' @param unit What a row is, for the texts; default "participants".
#' @return A `hairline_study`.
#' @export
hl_study <- function(data, group = NULL, time = NULL, event = NULL, id = NULL, variables = NULL, labels = NULL,
                     types = NULL, order = NULL, unit = NULL) {
  roles <- Filter(Negate(is.null), list(group = group, time = time, event = event, id = id))
  variables <- variables %||% setdiff(names(data), unlist(roles))
  kinds <- vapply(intersect(variables, names(data)), function(name) {
    types[[name]] %||% infer_study_type(data[[name]])
  }, character(1))
  has_group <- !is.null(group) && group %in% names(data)
  groups <- order %||% if (has_group) study_levels(data[[group]], FALSE) else character()
  checks <- run_study_checks(data, roles, variables, groups)
  study <- structure(list(data = data, roles = roles, variables = variables, labels = as.list(labels), types = kinds,
                          groups = groups, unit = unit %||% hl_tokens()$study$unit, checks = checks),
                     class = "hairline_study")
  if (length(checks)) {
    errors <- sum(vapply(checks, function(finding) finding$level == "error", logical(1)))
    warning(sprintf("hairline: study: %d errors, %d warnings; print the study to read them", errors,
                    length(checks) - errors), call. = FALSE)
  }
  study
}

#' @export
print.hairline_study <- function(x, ...) {
  roles <- if (length(x$roles)) paste(names(x$roles), "=", unlist(x$roles), collapse = ", ") else "no roles"
  cat(sprintf("Study of %d %s: %s; %d variables\n", nrow(x$data), x$unit, roles, length(x$variables)))
  lines <- if (length(x$checks)) vapply(x$checks, format_finding, character(1)) else "no problems found"
  cat(paste0("- ", lines, "\n"), sep = "")
  invisible(x)
}

study_label <- function(study, column) study$labels[[column]] %||% humanise(column)

study_require <- function(study, columns, endpoint) {
  errors <- Filter(function(finding) finding$level == "error" && finding$column %in% columns, study$checks)
  if (length(errors)) {
    stop(sprintf("hairline: %s: fix these first:\n%s", endpoint,
                 paste0("- ", vapply(errors, format_finding, character(1)), collapse = "\n")), call. = FALSE)
  }
}

study_result <- function(figure, table, values, text) {
  structure(list(figure = figure, table = table, values = values, text = text), class = "hairline_result")
}

#' @export
print.hairline_result <- function(x, ...) {
  cat(x$text, "\n\n", sep = "")
  print(x$table, row.names = FALSE, right = FALSE)
  invisible(x)
}
