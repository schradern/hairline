# Scatter with fit, mirroring the Python scatter(): points per group, a linear fit with its
# 95 % band in ink, and n, r and slope as key numbers.

scatter_stats <- function(x, y) {
  c(n = hl_format_number(length(x), 0), r = hl_format_number(pearson_test(x, y)[1], 2),
    Slope = hl_format_number(linear_fit(x, y)$slope, significant_places(linear_fit(x, y)$slope)))
}

scatter_fit_layers <- function(x, y) {
  settings <- hl_settings()
  rules <- hl_tokens()$fit
  xs <- seq(min(x), max(x), length.out = rules$points)
  band <- fit_band(linear_fit(x, y), xs)
  frame <- data.frame(x = xs, y = band$centre, low = band$low, high = band$high)
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
#' @return A ggplot with the hairline frame.
#' @examples
#' hl_scatter(datasets::mtcars, "wt", "mpg", title = "Fuel use by weight")
#' @export
hl_scatter <- function(data, x, y, by = NULL, title = NULL, subtitle = NULL, caption = NULL, fit = "linear",
                       order = NULL, colors = NULL) {
  check_columns(data, c(x, y, by))
  if (!is.null(fit) && !identical(fit, "linear")) {
    stop(sprintf("hairline: scatter: fit '%s' must be 'linear' or NULL", fit), call. = FALSE)
  }
  rows <- data[stats::complete.cases(data[, c(x, y)]), , drop = FALSE]
  if (!nrow(rows)) stop(sprintf("hairline: scatter: no rows with both '%s' and '%s' to draw", x, y), call. = FALSE)
  groups <- chart_groups(rows, by, order, "scatter")
  # The fit and its key numbers cover the points drawn: the groups in `order`, when given.
  if (!is.null(by)) rows <- rows[as.character(rows[[by]]) %in% groups, , drop = FALSE]
  colours <- if (is.null(by)) stats::setNames(lone_colour(), "") else
    colours_for(groups, colors)
  plot <- ggplot2::ggplot()
  for (name in groups) {
    subset <- if (is.null(by)) rows else rows[as.character(rows[[by]]) == name, , drop = FALSE]
    points <- data.frame(x = subset[[x]], y = subset[[y]], group = factor(name, levels = groups))
    plot <- plot + ggplot2::geom_point(data = points, ggplot2::aes(.data$x, .data$y, colour = .data$group))
  }
  plot <- plot + ggplot2::scale_colour_manual(values = colours, guide = if (is.null(by)) "none" else "legend")
  if (!is.null(fit)) {
    scatter_check_fit(rows[[x]])
    plot <- plot + scatter_fit_layers(rows[[x]], rows[[y]]) +
      hl_panel_header(name = "Linear fit", stats = scatter_stats(rows[[x]], rows[[y]]))
  }
  plot + ggplot2::labs(title = title %||% paste(humanise(y), "and", gsub("_", " ", x)), subtitle = subtitle,
                       caption = caption, x = humanise(x), y = humanise(y)) + theme_hairline()
}
