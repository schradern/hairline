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
  whole <- is_whole(study_numbers(study$data[[name]]))
  rows <- lapply(stats, function(stat) {
    c(paste0(study_label_unit(study, name), ", ", study_stat_labels[[stat]]),
      vapply(parts, function(part) {
        numeric_summary(study_numbers(part$rows[[name]]), stat, digits, sum(study_is_missing(part$rows[[name]])),
                        whole)
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
  colours <- if (is.null(study$roles$group)) stats::setNames(hl_settings()$palette[1], names) else
    colours_for(names, NULL)
  title <- if (is.null(study$roles$group)) "Characteristics" else
    paste("Characteristics by", gsub("_", " ", study$roles$group))
  settings <- hl_settings()
  range <- ggplot2::geom_path(data = ranges, ggplot2::aes(.data$x, .data$y, group = .data$group),
                              colour = settings$neutral$faint, lineend = "butt", inherit.aes = FALSE,
                              linewidth = pt_to_linewidth(hl_tokens()$reference$width * settings$base_size))
  range$hairline_fixed <- TRUE
  half <- spread_rules$band / 2
  plot <- ggplot2::ggplot(rows) + range +
    ggplot2::geom_rect(ggplot2::aes(xmin = .data$q1, xmax = .data$q3, ymin = .data$y - half, ymax = .data$y + half,
                                    fill = .data$group), alpha = spread_rules$band_opacity, colour = NA) +
    ggplot2::geom_point(ggplot2::aes(.data$middle, .data$y, colour = .data$group)) +
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
