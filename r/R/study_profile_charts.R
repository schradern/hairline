# The three kinds of hl_profile() tile and the figure that sets them in a grid. As the Python package's
# numeric_tile(), categorical_tile(), date_tile() and profile_figure().

# The x tick target of a tile in a grid `columns` wide (5, 4, then 3), as Python's tick_target() for the figure.
profile_tick_target <- function(columns) if (columns == 1) 5 else if (columns == 2) 4 else 3

# A histogram on round bins shared by every group, the median of all as an ink line; the header gives median (IQR)
# and what is missing.
profile_numeric_tile <- function(study, name, groups, legend, columns) {
  column <- study$data[[name]]
  label <- study_label(study, name)
  values <- study_numbers(column)
  found <- summary_numbers(values, "median_iqr", sum(study_is_missing(column)))
  whole <- is_whole(values)
  header <- hl_panel_header(name = label, qualifier = profile_missing_note(column),
                            x_title = study_measure(study, name),
                            stats = c(`Median (IQR)` = summary_text(found, "median_iqr", study_digits(values), whole)))
  scales <- list(integer_scale(), scale_x_hairline(target = profile_tick_target(columns)))
  if (!length(values)) return(profile_tile(scales, header, legend, list()))
  edges <- bin_edges(values, whole)
  width <- edges[2] - edges[1]
  lefts <- edges[-length(edges)]
  parts <- lapply(groups$strata, function(stratum) {
    list(stratum = stratum, values = counts_in(study_numbers(column[stratum$mask]), edges))
  })
  sizes <- vapply(groups$strata, function(stratum) length(study_numbers(column[stratum$mask])), numeric(1))
  names(sizes) <- vapply(groups$strata, function(stratum) stratum$name %||% ".all", "")
  tip <- function(spot, stratum, count) {
    span <- paste(c(profile_bin_text(lefts[spot], width, whole, study_digits(values)), study_measure(study, name)),
                  collapse = " ")
    paste0(label, " ", span, profile_in_group(stratum), ": ", count_share(count, sizes[[stratum$name %||% ".all"]]))
  }
  stacked <- profile_stack(parts, groups$colours, data.frame(low = lefts, high = lefts + width), FALSE, label, tip)
  median <- density_quantiles(values, 0.5)
  settings <- hl_settings()
  line <- ggplot2::annotate("segment", x = median, xend = median, y = 0, yend = max(stacked$totals),
                            colour = settings$neutral$ink, lineend = "butt",
                            linewidth = pt_to_linewidth(hl_tokens()$reference$width * settings$base_size))
  line$hairline_fixed <- TRUE
  profile_tile(c(list(profile_rect_layer(stacked$rects, settings), static_layer(line),
                      profile_count_reach(stacked$totals)), scales), header, legend,
               stacked$targets)
}

# One bar per level, its share of the non-missing values written at its end, split by group; short lists keep thin
# bars.
profile_categorical_tile <- function(study, name, groups, legend, columns) {
  rules <- hl_tokens()$profile
  column <- study$data[[name]]
  label <- study_label(study, name)
  present <- ifelse(study_is_missing(column), NA, level_text(column))
  kinds <- study_levels(column)
  header <- hl_panel_header(name = label, qualifier = profile_missing_note(column))
  # Shares run from none to all, whatever the largest share is.
  x_scale <- list(scale_x_hairline(percent = TRUE, target = profile_tick_target(columns)),
                  ggplot2::geom_blank(ggplot2::aes(x = .data$x), data = data.frame(x = c(0, 1)), inherit.aes = FALSE))
  if (!length(kinds)) return(profile_tile(x_scale, header, legend, list()))
  total <- sum(!is.na(present))
  parts <- lapply(groups$strata, function(stratum) {
    list(stratum = stratum, values = vapply(kinds, function(kind) sum(present[stratum$mask] == kind, na.rm = TRUE),
                                            numeric(1), USE.NAMES = FALSE) / total)
  })
  spots <- length(kinds) - seq_along(kinds)
  half <- rules$bar_height / 2
  tip <- function(spot, stratum, share) {
    paste0(label, " ", kinds[spot], profile_in_group(stratum), ": ", count_share(round(share * total), total))
  }
  stacked <- profile_stack(parts, groups$colours, data.frame(low = spots - half, high = spots + half), TRUE, label,
                           tip)
  settings <- hl_settings()
  shares <- data.frame(x = stacked$totals, y = spots,
                       label = vapply(stacked$totals, hl_format_percent, "", digits = 0))
  values <- bar_text(ggplot2::aes(.data$x, .data$y, label = .data$label), shares, "identity", settings$neutral$muted,
                     settings, hjust = -hl_tokens()$bars$label_gap, vjust = 0.5, inherit.aes = FALSE)
  slots <- max(length(kinds), rules$min_slots)
  y_scale <- ggplot2::scale_y_continuous(breaks = spots, labels = kinds, expand = c(0, 0),
                                         limits = c(length(kinds) - 0.5 - slots, length(kinds) - 0.5))
  profile_tile(c(list(profile_rect_layer(stacked$rects, settings), values, y_scale), x_scale), header, legend,
               stacked$targets)
}
