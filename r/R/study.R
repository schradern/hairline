# A study: a dataset described once, checked when it is created, mirroring hl.study().

study_kinds <- c("numeric", "categorical")

# Variables are numeric or categorical; dates are followed over time, not summarised in a table.
study_check_kinds <- function(kinds) {
  for (name in names(kinds)) {
    if (kinds[[name]] == "date") {
      stop(sprintf(paste("hairline: study: '%s' holds dates, which tables do not summarise; leave it out of",
                         "variables and follow a measure over it with hl_over_time()"), name), call. = FALSE)
    }
    if (!kinds[[name]] %in% study_kinds) {
      stop(sprintf("hairline: study: type '%s' for '%s' is not one of %s", kinds[[name]], name,
                   paste(study_kinds, collapse = ", ")), call. = FALSE)
    }
  }
}

# The variable's type; a role column (follow-up time) is typed from its values.
study_kind <- function(study, column, endpoint) {
  if (!column %in% names(study$data)) {
    stop(sprintf("hairline: %s: '%s' is not a column of the study; columns: %s", endpoint, column,
                 paste(names(study$data), collapse = ", ")), call. = FALSE)
  }
  if (column %in% names(study$types)) study$types[[column]] else infer_study_type(study$data[[column]])
}

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
#' @param id Participant id, checked for duplicates; [hl_describe()], [hl_compare()] and [hl_distribution()]
#'   refuse a variable with more than one row per id.
#' @param variables Characteristics to describe; default every other column.
#' @param labels Named display names, e.g. `c(sofa = "SOFA score")`.
#' @param types Named types overriding the inference, e.g. `c(score = "categorical")`.
#' @param order Group order; default order of first appearance.
#' @param unit What a row is, for the texts; default "participants".
#' @param units Named units of numeric columns, e.g. `c(age = "years", lactate = "mmol/l")`; tables, panel
#'   headers and texts name them.
#' @return A `hairline_study`.
#' @examples
#' set.seed(1)
#' cohort <- data.frame(arm = rep(c("Standard care", "Early mobilisation"), each = 40),
#'                      age = round(stats::rnorm(80, 64, 12)),
#'                      sex = sample(c("Female", "Male"), 80, TRUE),
#'                      months = round(stats::rexp(80, 0.05), 1), died = stats::rbinom(80, 1, 0.4))
#' study <- hl_study(cohort, group = "arm", time = "months", event = "died",
#'                   units = c(age = "years", months = "months"))
#' study
#' @export
hl_study <- function(data, group = NULL, time = NULL, event = NULL, id = NULL, variables = NULL, labels = NULL,
                     types = NULL, order = NULL, unit = NULL, units = NULL) {
  if (!nrow(data)) stop("hairline: study: the data has no rows", call. = FALSE)
  roles <- Filter(Negate(is.null), list(group = group, time = time, event = event, id = id))
  others <- setdiff(names(data), unlist(roles))
  variables <- variables %||% others[vapply(others, function(name) infer_study_type(data[[name]]) != "date",
                                            logical(1))]
  types <- as.list(types)
  kinds <- vapply(intersect(variables, names(data)), function(name) {
    types[[name]] %||% infer_study_type(data[[name]])
  }, character(1))
  study_check_kinds(kinds)
  has_group <- !is.null(group) && group %in% names(data)
  study_check_order(order)
  groups <- order %||% if (has_group) study_levels(data[[group]], FALSE) else character()
  checks <- c(run_study_checks(data, roles, variables, groups), unit_findings(roles, variables, kinds, as.list(units)))
  study <- structure(list(data = data, roles = roles, variables = variables, labels = as.list(labels), types = kinds,
                          groups = groups, unit = unit %||% hl_tokens()$study$unit, checks = checks,
                          units = as.list(units)),
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

# Each group once in `order`; a repeated name would analyse the same rows twice.
study_check_order <- function(order) {
  counts <- table(factor(order, levels = unique(order)))
  repeated <- names(counts)[counts > 1]
  if (length(repeated)) {
    count <- counts[[repeated[1]]]
    stop(sprintf("hairline: study: order names '%s' %s; name each group once", repeated[1],
                 if (count == 2) "twice" else paste(count, "times")), call. = FALSE)
  }
}

# The column endpoints add for the group as text, named so it never collides with a column of the data.
study_group_key <- function(study) {
  name <- ".group"
  while (name %in% names(study$data)) name <- paste0(".", name)
  name
}

# The label of all rows together: "Overall", unless a group already has that name.
study_overall <- function(study) {
  name <- "Overall"
  while (name %in% study$groups) name <- paste(name, "(all)")
  name
}

study_label <- function(study, column) study$labels[[column]] %||% humanise(column)

# The column's unit; none when the label already says it ("Months").
study_measure <- function(study, column) {
  unit <- study$units[[column]]
  if (!is.null(unit) && tolower(unit) == tolower(study_label(study, column))) NULL else unit
}

study_label_unit <- function(study, column) {
  unit <- study_measure(study, column)
  if (is.null(unit)) study_label(study, column) else sprintf("%s (%s)", study_label(study, column), unit)
}

# Numeric variables (and follow-up time) need a unit, so mixed tables and panels say what they measure.
unit_findings <- function(roles, variables, types, units) {
  measured <- c(roles$time, variables[variables %in% names(types) & types[variables] == "numeric"])
  missing <- measured[!vapply(measured, function(name) nzchar(units[[name]] %||% ""), logical(1))]
  if (!length(missing)) return(list())
  list(study_finding("warning", paste(missing, collapse = ", "), "numeric columns without a unit", integer(),
                     "give each a unit, for example years or mmol/l, so tables and panels name it"))
}

study_require <- function(study, columns, endpoint) {
  errors <- Filter(function(finding) finding$level == "error" && finding$column %in% columns, study$checks)
  if (length(errors)) {
    stop(sprintf("hairline: %s: fix these first:\n%s", endpoint,
                 paste0("- ", vapply(errors, format_finding, character(1)), collapse = "\n")), call. = FALSE)
  }
}

# Refuse to count repeated rows of one id as separate patients, in every row (counts, events and values all count
# rows); name the id and the most rows per id.
study_require_one_row <- function(study, endpoint) {
  name <- study$roles$id
  if (is.null(name) || !name %in% names(study$data)) return(invisible())
  ids <- level_text(study$data[[name]][!study_is_missing(study$data[[name]])])
  if (!length(ids)) return(invisible())
  counts <- sort(table(ids), decreasing = TRUE)
  if (counts[[1]] > 1) {
    stop(sprintf(paste("hairline: %s: id %s has %d rows in '%s', and each would count as one of the %s; summarise to",
                       "one row per id first (for example each patient's first value), or follow repeated",
                       "measurements with hl_over_time()"), endpoint, names(counts)[1], counts[[1]], name, study$unit),
         call. = FALSE)
  }
}

# The formatted table, values and text, and the unrounded numbers they are formatted from.
study_result <- function(figure, table, values, text, numbers) {
  structure(list(figure = figure, table = table, values = values, text = text, numbers = numbers),
            class = "hairline_result")
}

#' @export
print.hairline_result <- function(x, ...) {
  cat(x$text, "\n\n", sep = "")
  print(x$table, row.names = FALSE, right = FALSE)
  invisible(x)
}
