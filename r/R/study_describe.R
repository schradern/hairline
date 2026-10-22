# hl_describe(): Table 1 by group, values per variable, a counts sentence and an overview of the numeric variables.

study_subsets <- function(study) {
  overall <- list(list(name = study_overall(study), rows = study$data))
  if (is.null(study$roles$group)) return(overall)
  values <- study$data[[study$roles$group]]
  labels <- ifelse(study_is_missing(values), NA, level_text(values))
  c(lapply(study$groups, function(name) {
    list(name = name, rows = study$data[!is.na(labels) & labels == name, , drop = FALSE])
  }), overall)
}

study_part_names <- function(parts) vapply(parts, `[[`, character(1), "name")

describe_numeric <- function(study, name, parts, stats) {
  digits <- study_digits(study_numbers(study$data[[name]]))
  whole <- is_whole(study_numbers(study$data[[name]]))
  found <- stats::setNames(lapply(parts, function(part) {
    summary_numbers(study_numbers(part$rows[[name]]), stats, sum(study_is_missing(part$rows[[name]])))
  }), study_part_names(parts))
  rows <- lapply(stats, function(stat) {
    c(paste0(study_label_unit(study, name), ", ", study_stat_labels[[stat]]),
      vapply(found, summary_text, character(1), stat = stat, digits = digits, whole = whole, USE.NAMES = FALSE))
  })
  values <- stats::setNames(as.list(rows[[1]][-1]), names(found))
  list(rows = rows, values = stats::setNames(list(values), name), numbers = found)
}

# n and missing, then the count and share (of the non-missing values) of each level.
level_numbers <- function(values, kinds) {
  present <- level_text(values[!study_is_missing(values)])
  counts <- stats::setNames(lapply(kinds, function(kind) sum(present == kind)), kinds)
  list(n = length(present), missing = length(values) - length(present), counts = counts,
       shares = lapply(counts, share_of, total = length(present)))
}

describe_categorical <- function(study, name, parts) {
  kinds <- study_levels(study$data[[name]])
  found <- stats::setNames(lapply(parts, function(part) level_numbers(part$rows[[name]], kinds)),
                           study_part_names(parts))
  header <- c(paste0(study_label(study, name), ", n (%)"), rep("", length(parts)))
  level_rows <- lapply(kinds, function(kind) {
    c(paste0("  ", kind), vapply(found, function(part) count_share(part$counts[[kind]], part$n), character(1),
                                 USE.NAMES = FALSE))
  })
  rows <- c(list(header), level_rows)
  values <- stats::setNames(lapply(seq_along(parts), function(index) {
    stats::setNames(lapply(rows[-1], function(row) row[index + 1]), kinds)
  }), names(found))
  list(rows = rows, values = stats::setNames(list(values), name), numbers = found)
}

study_group_role <- function(study) if (is.null(study$roles$group)) list() else list(group = study$roles$group)

# Rows in the study, analysed, and missing: each role in turn (variable, group, date) counts the rows still in that
# lack it. With a group, other_groups counts rows in groups that order leaves out; with `in_overall` those and the
# rows without a group still count as analysed, in Overall.
study_counted_rows <- function(study, columns, in_overall = FALSE) {
  data <- study$data
  kept <- rep(TRUE, nrow(data))
  missing <- stats::setNames(list(), character())
  for (role in names(columns)) {
    absent <- study_is_missing(data[[columns[[role]]]])
    missing[[role]] <- sum(kept & absent)
    kept <- kept & !absent
  }
  found <- list(total = nrow(data), analysed = 0L, missing = missing)
  group <- study$roles$group
  if (!is.null(group)) {
    other <- kept & !level_text(data[[group]]) %in% study$groups
    found$other_groups <- sum(other)
    kept <- kept & !other
  }
  overall <- if (in_overall) (missing$group %||% 0L) + (found$other_groups %||% 0L) else 0L
  found$analysed <- sum(kept) + overall
  found
}

describe_text <- function(study, parts, counts) {
  total <- counted_text(nrow(parts[[length(parts)]]$rows), study_nouns(study))
  if (is.null(study$roles$group)) return(paste0(total, "."))
  groups <- paste(counts[-length(counts)], "in", study_part_names(parts[-length(parts)]))
  paste0(total, ": ", listed_text(groups), ".")
}

# " Left out where missing: Age 1 and SOFA 2."; empty when no variable misses a value.
describe_missing_text <- function(study, found) {
  missing <- vapply(study$variables, function(name) found$variables[[name]][[study_overall(study)]]$missing,
                    numeric(1))
  if (!any(missing > 0)) return("")
  parts <- paste(vapply(study$variables[missing > 0], study_label, character(1), study = study),
                 vapply(missing[missing > 0], hl_format_number, character(1), digits = 0))
  sprintf(" Left out where missing: %s.", listed_text(parts))
}

#' Table 1: the cohort by group
#'
#' One row per statistic or category, one column per group plus Overall,
#' with an overview figure of the numeric variables (median and IQR).
#'
#' @param study A study from [hl_study()].
#' @param stats Statistics for numeric variables: `"median_iqr"`, `"mean_sd"`, `"range"`, `"n_missing"`.
#' @return A `hairline_result`: `figure`, `table`, `values`, `text` and the unrounded `numbers` they are formatted
#'   from (per group n, rows missing a value or a group, and the statistics).
#' @examples
#' set.seed(1)
#' cohort <- data.frame(arm = rep(c("Standard care", "Early mobilisation"), each = 40),
#'                      age = round(stats::rnorm(80, 64, 12)),
#'                      sex = sample(c("Female", "Male"), 80, TRUE),
#'                      months = round(stats::rexp(80, 0.05), 1), died = stats::rbinom(80, 1, 0.4))
#' study <- hl_study(cohort, group = "arm", time = "months", event = "died",
#'                   units = c(age = "years", months = "months"))
#' table_one <- hl_describe(study)
#' table_one$table
#' table_one$figure
#' @export
hl_describe <- function(study, stats = "median_iqr") {
  check_study_stats(stats)
  study_require(study, c(study$roles$group, study$variables), "describe")
  study_require_one_row(study, "describe")
  parts <- study_subsets(study)
  names <- study_part_names(parts)
  found <- list(rows = study_counted_rows(study, study_group_role(study), in_overall = TRUE),
                n = stats::setNames(lapply(parts, function(part) nrow(part$rows)), names), variables = list())
  counts <- vapply(found$n, hl_format_number, character(1), digits = 0, USE.NAMES = FALSE)
  rows <- list(c("n", counts))
  values <- list(n = stats::setNames(as.list(counts), names))
  for (name in study$variables) {
    described <- if (study$types[[name]] == "numeric") describe_numeric(study, name, parts, stats) else
      describe_categorical(study, name, parts)
    rows <- c(rows, described$rows)
    values <- c(values, described$values)
    found$variables[[name]] <- described$numbers
  }
  table <- as.data.frame(do.call(rbind, rows), stringsAsFactors = FALSE)
  names(table) <- c("Characteristic", names)
  text <- paste0(describe_text(study, parts, counts), overall_only_text(found$rows),
                 describe_missing_text(study, found))
  groups <- if (is.null(study$roles$group)) character() else utils::head(names, -1)
  study_result(study_figure("describe", groups, "groups", function() study_overview(study, parts)), table, values,
               text, found)
}

study_overview <- function(study, parts) {
  numeric <- study$variables[study$types[study$variables] == "numeric"]
  if (!length(numeric)) return(NULL)
  shown <- if (is.null(study$roles$group)) parts else parts[-length(parts)]
  names <- vapply(shown, `[[`, character(1), "name")
  rules <- hl_tokens()$study
  spread_rules <- hl_tokens()$spread
  columns <- min(length(numeric), rules$overview_columns)
  panel_rows <- ceiling(length(numeric) / columns)
  overview_rows <- function(name) {
    do.call(rbind, lapply(seq_along(shown), function(position) {
      limits <- density_quantiles(study_numbers(shown[[position]]$rows[[name]]), c(0, 0.25, 0.5, 0.75, 1))
      data.frame(variable = study_label(study, name), group = shown[[position]]$name,
                 y = length(shown) - position, low = limits[1], q1 = limits[2], middle = limits[3], q3 = limits[4],
                 high = limits[5])
    }))
  }
  rows <- do.call(rbind, lapply(numeric, overview_rows))
  rows$variable <- factor(rows$variable, levels = vapply(numeric, study_label, character(1), study = study))
  rows$group <- factor(rows$group, levels = names)
  ranges <- rbind(cbind(rows, x = rows$low), cbind(rows, x = rows$high))
  colours <- if (is.null(study$roles$group)) stats::setNames(lone_colour(), names) else
    colours_for(names, NULL)
  title <- if (is.null(study$roles$group)) "Characteristics" else
    paste("Characteristics by", study_in_sentence(study, study$roles$group))
  settings <- hl_settings()
  range <- ggplot2::geom_path(data = ranges, ggplot2::aes(.data$x, .data$y, group = .data$group),
                              colour = settings$neutral$faint, lineend = "butt", inherit.aes = FALSE,
                              linewidth = pt_to_linewidth(hl_tokens()$reference$width * settings$base_size))
  range$hairline_fixed <- TRUE
  half <- spread_rules$band / 2
  plot <- ggplot2::ggplot(rows) + range +
    ggplot2::geom_rect(ggplot2::aes(xmin = .data$q1, xmax = .data$q3, ymin = .data$y - half, ymax = .data$y + half,
                                    fill = .data$group), alpha = spread_rules$band_opacity, colour = NA) +
    static_layer(ggplot2::geom_point(ggplot2::aes(.data$middle, .data$y, colour = .data$group))) +
    ggplot2::facet_wrap(~variable, ncol = columns, scales = "free_x") +
    ggplot2::scale_y_continuous(breaks = rev(seq_along(names) - 1), labels = names,
                                limits = c(-0.6, length(names) - 0.4), expand = c(0, 0)) +
    ggplot2::scale_colour_manual(values = colours, guide = "none") +
    ggplot2::scale_fill_manual(values = colours, guide = "none") +
    ggplot2::labs(title = title, subtitle = "Range, interquartile range and median", x = NULL, y = NULL) +
    theme_hairline() + hl_legend(list())
  for (name in numeric) {
    plot <- plot + hl_panel_header(panel = study_label(study, name), x_title = study_measure(study, name))
  }
  plot@meta$hairline_height_mm <- rules$overview_frame_mm +
    panel_rows * (rules$overview_panel_mm + length(shown) * rules$overview_row_mm)
  plot
}
