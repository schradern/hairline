# hl_describe(): Table 1 by group, values per variable, a counts sentence and an overview of the numeric variables.

study_subsets <- function(study) {
  overall <- list(list(name = "Overall", rows = study$data))
  if (is.null(study$roles$group)) return(overall)
  values <- study$data[[study$roles$group]]
  labels <- ifelse(study_is_missing(values), NA, level_text(values))
  c(lapply(study$groups, function(name) {
    list(name = name, rows = study$data[!is.na(labels) & labels == name, , drop = FALSE])
  }), overall)
}

describe_numeric <- function(study, name, parts, stats) {
  digits <- study_digits(study_numbers(study$data[[name]]))
  rows <- lapply(stats, function(stat) {
    c(paste0(study_label_unit(study, name), ", ", study_stat_labels[[stat]]),
      vapply(parts, function(part) {
        numeric_summary(study_numbers(part$rows[[name]]), stat, digits, sum(study_is_missing(part$rows[[name]])))
      }, character(1)))
  })
  values <- stats::setNames(as.list(rows[[1]][-1]), vapply(parts, `[[`, character(1), "name"))
  list(rows = rows, values = stats::setNames(list(values), name))
}

describe_categorical <- function(study, name, parts) {
  kinds <- study_levels(study$data[[name]])
  presents <- lapply(parts, function(part) {
    values <- part$rows[[name]]
    level_text(values[!study_is_missing(values)])
  })
  header <- c(paste0(study_label(study, name), ", n (%)"), rep("", length(parts)))
  level_rows <- lapply(kinds, function(kind) {
    c(paste0("  ", kind), vapply(presents, function(present) count_share(sum(present == kind), length(present)),
                                 character(1)))
  })
  rows <- c(list(header), level_rows)
  values <- stats::setNames(lapply(seq_along(parts), function(index) {
    stats::setNames(lapply(rows[-1], function(row) row[index + 1]), kinds)
  }), vapply(parts, `[[`, character(1), "name"))
  list(rows = rows, values = stats::setNames(list(values), name))
}

describe_text <- function(study, parts, counts) {
  total <- paste(counts[length(counts)], study$unit)
  if (is.null(study$roles$group)) return(paste0(total, "."))
  groups <- paste(counts[-length(counts)], "in", vapply(parts[-length(parts)], `[[`, character(1), "name"))
  paste0(total, ": ", listed_text(groups), ".")
}

#' Table 1: the cohort by group
#'
#' One row per statistic or category, one column per group plus Overall,
#' with an overview figure of the numeric variables (median and IQR).
#'
#' @param study A study from [hl_study()].
#' @param stats Statistics for numeric variables: `"median_iqr"`, `"mean_sd"`, `"range"`, `"n_missing"`.
#' @return A `hairline_result`: `figure`, `table`, `values` and `text`.
#' @export
hl_describe <- function(study, stats = "median_iqr") {
  check_study_stats(stats)
  study_require(study, c(study$roles$group, study$variables), "describe")
  parts <- study_subsets(study)
  names <- vapply(parts, `[[`, character(1), "name")
  counts <- vapply(parts, function(part) hl_format_number(nrow(part$rows), 0), character(1))
  rows <- list(c("n", counts))
  values <- list(n = stats::setNames(as.list(counts), names))
  for (name in study$variables) {
    found <- if (study$types[[name]] == "numeric") describe_numeric(study, name, parts, stats) else
      describe_categorical(study, name, parts)
    rows <- c(rows, found$rows)
    values <- c(values, found$values)
  }
  table <- as.data.frame(do.call(rbind, rows), stringsAsFactors = FALSE)
  names(table) <- c("Characteristic", names)
  study_result(study_overview(study, parts), table, values, describe_text(study, parts, counts))
}

study_overview <- function(study, parts) {
  numeric <- study$variables[study$types[study$variables] == "numeric"]
  if (!length(numeric)) return(NULL)
  shown <- if (is.null(study$roles$group)) parts else parts[-length(parts)]
  names <- vapply(shown, `[[`, character(1), "name")
  rules <- hl_tokens()$study
  columns <- min(length(numeric), rules$overview_columns)
  panel_rows <- ceiling(length(numeric) / columns)
  overview_rows <- function(name) {
    do.call(rbind, lapply(shown, function(part) {
      limits <- density_quantiles(study_numbers(part$rows[[name]]), c(0.25, 0.5, 0.75))
      data.frame(variable = study_label(study, name), group = part$name, x = limits[c(1, 3)], middle = limits[2])
    }))
  }
  lines <- do.call(rbind, lapply(numeric, overview_rows))
  lines$variable <- factor(lines$variable, levels = vapply(numeric, study_label, character(1), study = study))
  lines$group <- factor(lines$group, levels = rev(names))
  colours <- if (is.null(study$roles$group)) stats::setNames(hl_settings()$palette[1], names) else
    colours_for(names, NULL)
  title <- if (is.null(study$roles$group)) "Characteristics" else
    paste("Characteristics by", gsub("_", " ", study$roles$group))
  plot <- ggplot2::ggplot(lines, ggplot2::aes(y = .data$group, colour = .data$group)) +
    ggplot2::geom_path(ggplot2::aes(x = .data$x, group = .data$group), lineend = "butt") +
    ggplot2::geom_point(data = lines[!duplicated(lines[c("variable", "group")]), ], ggplot2::aes(x = .data$middle)) +
    ggplot2::facet_wrap(~variable, ncol = columns, scales = "free_x") +
    ggplot2::scale_colour_manual(values = colours, guide = "none") +
    ggplot2::labs(title = title, subtitle = "Median and interquartile range", x = NULL, y = NULL) + theme_hairline() +
    hl_legend(list())
  for (name in numeric) {
    plot <- plot + hl_panel_header(panel = study_label(study, name), qualifier = study_measure(study, name))
  }
  plot@meta$hairline_height_mm <- rules$overview_frame_mm +
    panel_rows * (rules$overview_panel_mm + length(shown) * rules$overview_row_mm)
  plot
}
