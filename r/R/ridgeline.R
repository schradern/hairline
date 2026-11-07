# Ridgeline plot, mirroring the Python ridgeline(): one density ridge per group on a shared x-axis, the first
# group on top, overlapping the row above, medians marked.

ridge_layers <- function(curve, values, base, scale, colour, medians, counted = values) {
  settings <- hl_settings()
  rules <- hl_tokens()$ridgeline
  outline <- data.frame(x = curve$grid, y = base + curve$height * scale)
  corners <- rbind(data.frame(x = curve$grid[1], y = base), outline,
                   data.frame(x = curve$grid[length(curve$grid)], y = base))
  layers <- list(ggplot2::geom_polygon(data = corners, ggplot2::aes(.data$x, .data$y), fill = settings$neutral$surface,
                                       colour = NA, inherit.aes = FALSE),
                 ggplot2::geom_polygon(data = corners, ggplot2::aes(.data$x, .data$y), fill = colour,
                                       alpha = rules$fill_opacity, colour = NA, inherit.aes = FALSE),
                 static_layer(ggplot2::geom_path(data = outline, ggplot2::aes(.data$x, .data$y), colour = colour,
                                                 linewidth = pt_to_linewidth(hl_tokens()$lines$data *
                                                                               settings$base_size),
                                                 inherit.aes = FALSE)))
  if (medians) {
    # The median of the values counted, held within the drawn ridge.
    middle <- min(max(density_quantiles(counted, 0.5), curve$grid[1]), curve$grid[length(curve$grid)])
    top <- base + stats::approx(curve$grid, curve$height, middle)$y * scale
    median <- ggplot2::geom_segment(data = data.frame(x = middle, y = base, yend = top),
                                    ggplot2::aes(.data$x, .data$y, xend = .data$x, yend = .data$yend),
                                    colour = settings$neutral$ink, inherit.aes = FALSE,
                                    linewidth = pt_to_linewidth(hl_tokens()$reference$width * settings$base_size))
    median$hairline_secondary <- TRUE
    layers[[4]] <- median
  }
  layers
}

# A group too small or too uniform for a density (one value, or all alike) shows each value as a spike, so its row is
# never empty.
ridge_spikes <- function(values, base, colour, rules) {
  shown <- sort(unique(as.numeric(values)))
  if (!length(shown)) return(list())
  spikes <- data.frame(x = shown, y = base, yend = base + rules$spike)
  list(static_layer(ggplot2::geom_segment(data = spikes, ggplot2::aes(.data$x, .data$y, xend = .data$x,
                                                                      yend = .data$yend), colour = colour,
                                          linewidth = pt_to_linewidth(hl_tokens()$lines$data * hl_settings()$base_size),
                                          inherit.aes = FALSE)))
}

# Each group's values among the rows `here` (all rows without a facet); a group absent there has none. As Python's
# panel_groups().
ridgeline_groups <- function(data, group, value, names, here) {
  stats::setNames(lapply(names, function(name) {
    as.numeric(stats::na.omit(data[[value]][here & as.character(data[[group]]) == name]))
  }), names)
}

# One panel's ridges, top row first, each lower ridge in front of the one above; a group without a density shows its
# values as spikes.
ridgeline_panel_layers <- function(drawn, curves, counted, scale, medians, palette) {
  rules <- hl_tokens()$ridgeline
  names <- names(drawn)
  layers <- list()
  for (index in seq_along(names)) {
    base <- length(names) - index
    layers <- c(layers, if (is.null(curves[[index]])) {
      ridge_spikes(drawn[[index]], base, palette[[names[index]]], rules)
    } else {
      ridge_layers(curves[[index]], drawn[[index]], base, scale, palette[[names[index]]], medians, counted[[index]])
    })
  }
  layers
}

#' Ridgeline plot
#'
#' One density ridge per group on a shared x-axis, the first group on top,
#' each overlapping the row above; all ridges share one height scale, and a
#' short line marks each median.
#'
#' @param data A data frame.
#' @param group,value Columns: the grouping and the measurement; or a formula `value ~ group` as `group`.
#' @param title,subtitle,caption Frame texts; the title defaults to the columns.
#' @param order Group order, top to bottom.
#' @param medians Mark the medians.
#' @param colors Named colours for this chart only, e.g. `c(Male = "#0a6ddd")`; they override the colour set
#'   for the number of groups and are not remembered for other charts.
#'   A ramp name such as `"blues"` colours ordered groups light to dark, in the chart's order.
#' @param show_n Write each group's n after its name, in the locale; with `facet`, each panel's n in its header.
#' @param min_n,clip,clip_stats,color_by,dimension As in [hl_spread()]: groups too small and values clipped off are
#'   named in the caption.
#' @param columns Panels per row with `facet` (two by default).
#' @inheritParams chart_option_params
#' @return A ggplot with the hairline frame.
#' @examples
#' set.seed(1)
#' diagnoses <- c("Sepsis", "Trauma", "Cardiac", "Respiratory", "Neuro")
#' ages <- data.frame(diagnosis = rep(diagnoses, each = 40),
#'                    age = round(stats::rnorm(200, rep(c(68, 45, 70, 62, 55), each = 40), 10)))
#' hl_ridgeline(ages, "diagnosis", "age")
#' @export
hl_ridgeline <- function(data, group, value = NULL, title = NULL, subtitle = NULL, caption = NULL, order = NULL,
                         medians = TRUE, colors = NULL, show_n = FALSE, min_n = NULL, clip = NULL, clip_stats = FALSE,
                         color_by = NULL, dimension = NULL, sort = NULL, percent = FALSE, x_title = NULL,
                         reference = NULL, highlight = NULL, key_title = NULL, facet = NULL, columns = NULL) {
  if (inherits(group, "formula")) {
    sides <- formula_sides(group)
    value <- deparse(sides$left)
    group <- sides$right[1]
  }
  check_columns(data, c(group, value, color_by, facet))
  check_present(data, value, "ridgeline")
  check_numeric(data, value, "ridgeline")
  rules <- hl_tokens()$ridgeline
  names <- chart_groups(data, group, order, "ridgeline")
  groups <- ridgeline_groups(data, group, value, names, rep(TRUE, nrow(data)))
  dropped <- drop_small(groups, min_n, "ridgeline")
  groups <- dropped$groups[sorted_names(names(dropped$groups), function(name) dropped$groups[[name]], sort,
                                        "ridgeline")]
  names <- names(groups)
  every <- unlist(groups, use.names = FALSE)
  limits <- clip_limits(every, clip, "ridgeline")
  panels <- if (is.null(facet)) "" else chart_groups(data, facet, NULL, "ridgeline")
  counted <- lapply(panels, function(panel) {
    if (is.null(facet)) groups else ridgeline_groups(data, group, value, names, as.character(data[[facet]]) == panel)
  })
  drawn <- lapply(counted, function(here) lapply(here, within_limits, limits = limits))
  curves <- lapply(drawn, function(here) lapply(here, density_curve))
  heights <- unlist(lapply(curves, function(here) lapply(here, function(curve) max(c(0, curve$height)))))
  peak <- max(c(0, heights))
  scale <- (1 + rules$overlap) / if (peak > 0) peak else 1
  palette <- series_colours(names, data, group, color_by, colors, dimension, "ridgeline", highlight)
  plot <- ggplot2::ggplot()
  for (index in seq_along(panels)) {
    statistics <- if (clip_stats) drawn[[index]] else counted[[index]]
    layers <- ridgeline_panel_layers(drawn[[index]], curves[[index]], statistics, scale, medians, palette$palette)
    plot <- plot + if (is.null(facet)) layers else in_facet(layers, panels[index], panels)
    if (!is.null(facet)) {
      total <- sum(lengths(statistics))
      plot <- plot + hl_panel_header(panel = panels[index], name = panels[index],
                                     stats = if (show_n) c(n = hl_format_number(total, 0)) else NULL)
    }
  }
  labels <- if (show_n && is.null(facet)) labels_with_n(names, lengths(groups)) else names
  notes <- c(dropped$note, if (!is.null(clip)) clip_caption(every, limits, clip_stats))
  plot <- plot + ggplot2::scale_y_continuous(breaks = rev(seq_along(names) - 1), labels = labels, expand = c(0, 0),
                                             limits = c(0, length(names) + rules$overlap + rules$headroom)) +
    ggplot2::labs(title = title %||% paste(humanise(value), "by", gsub("_", " ", group)), subtitle = subtitle,
                  caption = with_caption(caption, notes), x = humanise(value), y = NULL) + theme_hairline()
  if (!is.null(facet)) {
    plot <- plot + ggplot2::facet_wrap(ggplot2::vars(.data$.facet), ncol = columns %||% min(length(panels), 2))
  }
  if (!is.null(color_by)) plot <- plot + hl_legend(coarse_legend(palette))
  if (percent) plot <- plot + scale_x_hairline(percent = TRUE)
  chart_options(plot, "ridgeline", names, x_title = x_title, reference = reference, reference_axis = "x",
                key_title = key_title)
}
