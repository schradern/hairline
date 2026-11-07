# Scatter with fit, mirroring the Python scatter(): points per group, a linear fit with its
# 95 % band in ink, and n, r and slope as key numbers.

scatter_stats <- function(x, y) {
  c(n = hl_format_number(length(x), 0), r = hl_format_number(pearson_test(x, y)[1], 2),
    Slope = hl_format_number(linear_fit(x, y)$slope, significant_places(linear_fit(x, y)$slope)))
}

scatter_fit_layers <- function(x, y, facet = NULL) {
  settings <- hl_settings()
  rules <- hl_tokens()$fit
  xs <- seq(min(x), max(x), length.out = rules$points)
  band <- fit_band(linear_fit(x, y), xs)
  frame <- data.frame(x = xs, y = band$centre, low = band$low, high = band$high)
  if (!is.null(facet)) frame$.facet <- facet
  ink <- settings$neutral$ink
  list(ggplot2::geom_ribbon(data = frame, ggplot2::aes(.data$x, ymin = .data$low, ymax = .data$high), fill = ink,
                            alpha = rules$band_opacity, inherit.aes = FALSE),
       static_layer(ggplot2::geom_line(data = frame, ggplot2::aes(.data$x, .data$y), colour = ink, inherit.aes = FALSE,
                                       linewidth = pt_to_linewidth(hl_tokens()$lines$data * settings$base_size))))
}

# A line and its band need three points and two x values; fewer leave slope or band undefined.
scatter_check_fit <- function(x) {
  if (!is.numeric(x)) {
    stop(sprintf("hairline: scatter: a linear fit needs numbers on x; got %s; use fit = NULL for the points alone",
                 class(x)[1]), call. = FALSE)
  }
  distinct <- length(unique(x))
  if (length(x) < 3 || distinct < 2) {
    stop(sprintf(paste("hairline: scatter: a linear fit needs at least 3 points with x and y and 2 different x values;",
                       "got %d point(s) and %d x value(s); use fit = NULL for the points alone"), length(x), distinct),
         call. = FALSE)
  }
}

#' Scatter plot with fit
#'
#' Points per group in their entity colours and, with `fit = "linear"`, a
#' linear fit over all points with its 95 % band; n, r and slope become the
#' key numbers.
#'
#' @param data A data frame.
#' @param x,y Columns for the axes.
#' @param by Grouping column.
#' @param title,subtitle,caption Frame texts; the title defaults to the columns.
#' @param fit `"linear"` or `NULL`.
#' @param order Group order.
#' @param colors Named colours for this chart only, e.g. `c(Male = "#0a6ddd")`; they override the colour set
#'   for the number of groups and are not remembered for other charts.
#'   A ramp name such as `"blues"` colours ordered groups light to dark, in the chart's order.
#' @param clip,clip_stats Hide implausible y values, as in [hl_spread()], and say so in the caption; the fit still
#'   uses every point unless `clip_stats`.
#' @param color_by Colour the groups of `by` by a coarser column, which the legend lists.
#' @param dimension What the groups are, so their colours keep off the slots another dimension holds.
#' @param columns Panels per row with `facet` (two by default).
#' @inheritParams chart_option_params
#' @return A ggplot with the hairline frame.
#' @examples
#' hl_scatter(datasets::mtcars, "wt", "mpg", title = "Fuel use by weight")
#' @export
hl_scatter <- function(data, x, y, by = NULL, title = NULL, subtitle = NULL, caption = NULL, fit = "linear",
                       order = NULL, colors = NULL, clip = NULL, clip_stats = FALSE, color_by = NULL,
                       dimension = NULL, min_n = NULL, percent = FALSE, x_title = NULL, y_title = NULL,
                       reference = NULL, highlight = NULL, key_title = NULL, facet = NULL, columns = NULL) {
  check_columns(data, c(x, y, by, color_by, facet))
  if (!is.null(color_by) && is.null(by)) {
    stop("hairline: scatter: color_by needs by =, the groups it colours", call. = FALSE)
  }
  check_numeric(data, y, "scatter")
  check_finite(data, x, "scatter")
  if (!is.null(fit) && !identical(fit, "linear")) {
    stop(sprintf("hairline: scatter: fit '%s' must be 'linear' or NULL", fit), call. = FALSE)
  }
  rows <- data[stats::complete.cases(data[, c(x, y)]), , drop = FALSE]
  if (!nrow(rows)) stop(sprintf("hairline: scatter: no rows with both '%s' and '%s' to draw", x, y), call. = FALSE)
  kept <- if (is.null(by)) list(data = rows, note = NULL) else without_small_categories(rows, by, min_n, "scatter")
  rows <- kept$data
  groups <- chart_groups(rows, by, order, "scatter")
  # The fit and its key numbers cover the points drawn: the groups in `order`, when given.
  if (!is.null(by)) rows <- rows[as.character(rows[[by]]) %in% groups, , drop = FALSE]
  limits <- clip_limits(rows[[y]], clip, "scatter")
  note <- if (!is.null(clip)) clip_caption(rows[[y]], limits, clip_stats)
  coloured <- if (is.null(by)) list(palette = stats::setNames(lone_colour(), ""), coarse = NULL) else
    series_colours(groups, rows, by, color_by, colors, dimension, "scatter", highlight)
  panels <- if (is.null(facet)) "" else chart_groups(rows, facet, NULL, "scatter")
  plot <- ggplot2::ggplot()
  for (name in groups) {
    subset <- if (is.null(by)) rows else rows[as.character(rows[[by]]) == name, , drop = FALSE]
    subset <- subset[subset[[y]] >= limits[1] & subset[[y]] <= limits[2], , drop = FALSE]
    points <- data.frame(x = subset[[x]], y = subset[[y]], group = factor(rep(name, nrow(subset)), levels = groups))
    if (!is.null(facet)) points$.facet <- factor(as.character(subset[[facet]]), levels = panels)
    plot <- plot + ggplot2::geom_point(data = points, ggplot2::aes(.data$x, .data$y, colour = .data$group))
  }
  labels <- if (is.null(color_by)) ggplot2::waiver() else unname(coloured$coarse[groups])
  plot <- plot + ggplot2::scale_colour_manual(values = coloured$palette, breaks = names(coloured$palette),
                                              labels = labels, guide = if (is.null(by)) "none" else "legend")
  if (clip_stats) rows <- rows[rows[[y]] >= limits[1] & rows[[y]] <= limits[2], , drop = FALSE]
  for (panel in panels) {
    shown <- if (is.null(facet)) rows else rows[as.character(rows[[facet]]) == panel, , drop = FALSE]
    if (!is.null(fit)) {
      scatter_check_fit(shown[[x]])
      plot <- plot + scatter_fit_layers(shown[[x]], shown[[y]], if (is.null(facet)) NULL else
        factor(panel, levels = panels)) +
        hl_panel_header(panel = if (is.null(facet)) NULL else panel,
                        name = if (is.null(facet)) "Linear fit" else panel,
                        stats = scatter_stats(shown[[x]], shown[[y]]))
    } else if (!is.null(facet)) {
      plot <- plot + hl_panel_header(panel = panel, name = panel)
    }
  }
  if (!is.null(facet)) {
    plot <- plot + ggplot2::facet_wrap(ggplot2::vars(.data$.facet), ncol = columns %||% min(length(panels), 2))
  }
  # Limits end on a break, so a point at the limit would be cut in half by the panel's edge.
  plot <- plot + ggplot2::coord_cartesian(clip = "off") +
    ggplot2::labs(title = title %||% paste(humanise(y), "and", gsub("_", " ", x)), subtitle = subtitle,
                  caption = with_caption(caption, note, kept$note), x = humanise(x), y = humanise(y)) +
    theme_hairline()
  if (percent) plot <- plot + scale_y_hairline(percent = TRUE)
  chart_options(plot, "scatter", groups, x_title = x_title, y_title = y_title, reference = reference,
                key_title = key_title)
}
