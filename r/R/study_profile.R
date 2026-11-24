# hl_profile(): one cohort at a glance, each variable in a tile of its own beside its Table 1 rows; with `by`, every
# tile is split into the same coloured groups. As the Python package's study/profile.py and profile_strata.py.

profile_missing_group <- "Missing"

# A column of the data holding a few groups; numbers and dates are refused with what to pass instead.
profile_check_by <- function(study, by) {
  if (!by %in% names(study$data)) {
    stop(sprintf("hairline: profile: by '%s' is not a column of the data; columns: %s", by,
                 paste(names(study$data), collapse = ", ")), call. = FALSE)
  }
  kind <- if (by %in% names(study$types)) study$types[[by]] else infer_study_type(study$data[[by]])
  if (kind != "categorical") {
    stop(sprintf("hairline: profile: by '%s' holds %s; colour by a column of a few groups, such as sex or arm", by,
                 if (kind == "date") "dates" else "numbers"), call. = FALSE)
  }
  study_require(study, by, "profile")
}

# One stratum per group of `by` (the study's order for its own group), then the rows without one as 'Missing';
# without `by`, the whole cohort.
profile_strata <- function(study, by) {
  rows <- nrow(study$data)
  if (is.null(by)) return(list(list(name = NULL, mask = rep(TRUE, rows))))
  profile_check_by(study, by)
  column <- study$data[[by]]
  text <- ifelse(study_is_missing(column), NA, level_text(column))
  names <- if (identical(by, study$roles$group)) study$groups else study_levels(column)
  found <- lapply(names, function(name) list(name = name, mask = !is.na(text) & text == name))
  rest <- if (length(found)) !Reduce(`|`, lapply(found, `[[`, "mask")) else rep(TRUE, rows)
  c(found, if (any(rest)) list(list(name = profile_missing_group, mask = rest)))
}

profile_named <- function(strata) {
  Filter(function(stratum) !is.null(stratum$name) && stratum$name != profile_missing_group, strata)
}

# A column per group of `by`, then Overall (every row); without `by` only Overall.
profile_parts <- function(study, strata) {
  named <- lapply(profile_named(strata), function(stratum) {
    list(name = stratum$name, rows = study$data[stratum$mask, , drop = FALSE], mask = stratum$mask)
  })
  c(named, list(list(name = study_overall(study), rows = study$data, mask = rep(TRUE, nrow(study$data)))))
}

# 'Surgery date, first to last' and '2022-01-05 to 2024-12-28' per column (a dash without dates).
profile_date_rows <- function(study, name, dates, parts) {
  found <- list()
  spans <- character()
  for (part in parts) {
    days <- dates[part$mask[as.integer(names(dates))]]
    spans <- c(spans, if (length(days)) paste(format(min(days)), "to", format(max(days))) else "\u2013")
    found[[part$name]] <- list(n = length(days), missing = nrow(part$rows) - length(days),
                               first = if (length(days)) min(days), last = if (length(days)) max(days))
  }
  list(rows = list(c(paste0(study_label(study, name), ", first to last"), spans)),
       values = stats::setNames(list(stats::setNames(as.list(spans), study_part_names(parts))), name),
       numbers = found)
}

# '412 patients.', or by group: '412 patients; by sex, 181 Female and 231 Male. 3 without a sex are in Overall
# only.'
profile_counts_text <- function(study, strata, by) {
  total <- counted_text(nrow(study$data), study_nouns(study))
  if (is.null(by)) return(paste0(total, "."))
  counts <- vapply(profile_named(strata), function(stratum) {
    paste(hl_format_number(sum(stratum$mask), 0), stratum$name)
  }, "")
  rest <- sum(unlist(lapply(Filter(function(stratum) identical(stratum$name, profile_missing_group), strata),
                            function(stratum) sum(stratum$mask))))
  left <- if (rest) sprintf(" %s without a %s are in Overall only.", hl_format_number(rest, 0),
                            study_in_sentence(study, by)) else ""
  sprintf("%s; by %s, %s.%s", total, study_in_sentence(study, by), listed_text(counts), left)
}

# ' Missing: Weight 12.'; empty when every value is there.
profile_missing_text <- function(study, found) {
  missing <- vapply(names(found), function(name) found[[name]][[study_overall(study)]]$missing, numeric(1))
  if (!any(missing > 0)) return("")
  parts <- paste(vapply(names(found)[missing > 0], study_label, "", study = study),
                 vapply(missing[missing > 0], hl_format_number, "", digits = 0))
  sprintf(" Missing: %s.", listed_text(parts))
}

# The figure: one tile per variable, in the order given, the date columns last; one colour for the whole cohort, or
# the session's colour of each group with grey for rows without one, named once in the legend row.
profile_figure <- function(study, dates, strata, by, size) {
  names <- c(study$variables, names(dates))
  if (!length(names)) return(NULL)
  rules <- hl_tokens()$profile
  settings <- hl_settings()
  widths <- c(single = 1, onehalf = 2)
  columns <- min(length(names), if (size %in% names(widths)) widths[[size]] else rules$columns)
  groups <- list(strata = strata, colours = profile_colours(strata, settings))
  legend <- profile_legend(strata, groups$colours, if (!is.null(by)) study_label(study, by))
  tiles <- lapply(seq_along(names), function(index) {
    name <- names[index]
    own <- if (index == 1) legend else hl_legend(list())
    tile <- if (name %in% names(dates)) profile_date_tile(study, name, dates[[name]], groups, own) else
      if (study$types[[name]] == "numeric") profile_numeric_tile(study, name, groups, own, columns) else
        profile_categorical_tile(study, name, groups, own, columns)
    # The legend row names the groups once, after what they are.
    if (index == 1 && !is.null(by)) tile@meta$hairline_key_title <- study_label(study, by)
    tile
  })
  plot_grid(tiles, columns, title = "Characteristics of the cohort",
            subtitle = counted_text(nrow(study$data), study_nouns(study)),
            height_mm = rules$frame_mm + ceiling(length(names) / columns) * rules$tile_mm, size = size)
}

profile_colours <- function(strata, settings) {
  surface <- settings$neutral$surface
  if (is.null(strata[[1]]$name)) return(list(.all = profile_fill(lone_colour(settings), surface)))
  named <- vapply(profile_named(strata), `[[`, "", "name")
  colours <- c(as.list(colours_for(named, NULL)), stats::setNames(list(context_colour(settings)),
                                                                  profile_missing_group))
  lapply(colours, profile_fill, surface = surface)
}

profile_legend <- function(strata, colours, title) {
  if (is.null(title)) return(hl_legend(list()))
  items <- lapply(strata, function(stratum) {
    list(kind = "square", colour = colours[[stratum$name]], label = stratum$name)
  })
  hl_legend(items)
}

#' The cohort at a glance
#'
#' One tile per variable: a histogram for each number (its median as a line, median and IQR in the header), the
#' share of each level for each category and, for each column of `dates`, rows per month (quarter or year over long
#' periods). The table is Table 1 of the whole cohort. `by` names a column of a few groups (sex, arm) that splits
#' every tile into the session's colours, one legend for all; the table then has a column per group before Overall.
#'
#' @param study A study from [hl_study()].
#' @param dates Columns of dates or ISO date text (an operation date) to count per period.
#' @param by A column of a few groups to colour every tile by; `NULL` for the whole cohort in one colour.
#' @param size Size preset, as in [hl_save()]: three tiles a row across a page, two at `"onehalf"`, one at
#'   `"single"`.
#' @return A `hairline_result`: `figure`, `table`, `values`, `text` and the unrounded `numbers`.
#' @examples
#' set.seed(1)
#' cohort <- data.frame(sex = sample(c("Female", "Male"), 120, TRUE), age = round(stats::rnorm(120, 60, 12)),
#'                      operated = format(as.Date("2024-01-01") + sample(0:500, 120, TRUE)))
#' profile <- hl_profile(hl_study(cohort, variables = c("age", "sex"), units = c(age = "years")),
#'                       dates = "operated", by = "sex")
#' profile$table
#' profile$figure
#' @export
hl_profile <- function(study, dates = NULL, by = NULL, size = "double") {
  study_require(study, study$variables, "profile")
  study_require_one_row(study, "profile")
  check_size_preset(size)
  parsed <- stats::setNames(lapply(unique(dates), profile_dates, study = study), unique(dates))
  strata <- profile_strata(study, by)
  parts <- profile_parts(study, strata)
  counts <- vapply(parts, function(part) hl_format_number(nrow(part$rows), 0), "")
  rows <- list(c("n", counts))
  values <- list(n = stats::setNames(as.list(counts), study_part_names(parts)))
  found <- list()
  for (name in study$variables) {
    described <- if (study$types[[name]] == "numeric") describe_numeric(study, name, parts, "median_iqr") else
      describe_categorical(study, name, parts)
    rows <- c(rows, described$rows)
    values <- c(values, described$values)
    found[[name]] <- described$numbers
  }
  for (name in names(parsed)) {
    described <- profile_date_rows(study, name, parsed[[name]], parts)
    rows <- c(rows, described$rows)
    values <- c(values, described$values)
    found[[name]] <- described$numbers
  }
  table <- as.data.frame(do.call(rbind, rows), stringsAsFactors = FALSE)
  names(table) <- c("Characteristic", study_part_names(parts))
  text <- paste0(profile_counts_text(study, strata, by), profile_missing_text(study, found))
  named <- vapply(profile_named(strata), `[[`, "", "name")
  figure <- study_figure("profile", named, "groups", function() profile_figure(study, parsed, strata, by, size))
  study_result(figure, table, values, text, list(n = nrow(study$data), variables = found))
}
