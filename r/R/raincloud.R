# Raincloud, mirroring the Python raincloud(): per group a half density, the box (IQR and
# median) and the points, with "n = …" under the group names and comparison brackets stacked without overlap.

raincloud_group_layers <- function(values, position, colour, rules) {
  settings <- hl_settings()
  layers <- list()
  curve <- density_curve(values)
  if (!is.null(curve)) {
    start <- position + rules$density_offset
    outline <- data.frame(x = c(start, start + curve$height / max(curve$height) * rules$density_width, start),
                          y = c(curve$grid[1], curve$grid, curve$grid[length(curve$grid)]))
    layers[[1]] <- ggplot2::geom_polygon(data = outline, ggplot2::aes(.data$x, .data$y), fill = colour,
                                         alpha = rules$density_opacity, colour = NA, inherit.aes = FALSE)
  }
  limits <- density_quantiles(values, c(0.25, 0.5, 0.75))
  half <- rules$box_half
  box <- data.frame(xmin = position - half, xmax = position + half, ymin = limits[1], ymax = limits[3])
  median <- ggplot2::geom_segment(data = data.frame(x = position - half, xend = position + half, y = limits[2]),
                                  ggplot2::aes(.data$x, .data$y, xend = .data$xend, yend = .data$y),
                                  colour = settings$neutral$surface, lineend = "butt", inherit.aes = FALSE,
                                  linewidth = pt_to_linewidth(hl_tokens()$lines$data * settings$base_size))
  median$hairline_secondary <- TRUE
  points <- data.frame(x = position + rules$points_centre + jitter_offsets(length(values)) * rules$points_spread,
                       y = values)
  c(layers, list(ggplot2::geom_rect(data = box, ggplot2::aes(xmin = .data$xmin, xmax = .data$xmax,
                                                             ymin = .data$ymin, ymax = .data$ymax),
                                    fill = colour, colour = NA, inherit.aes = FALSE),
                 median,
                 static_layer(ggplot2::geom_point(data = points, ggplot2::aes(.data$x, .data$y), colour = colour,
                                                  inherit.aes = FALSE))))
}

raincloud_bracket_layers <- function(comparisons, names, values, rules) {
  settings <- hl_settings()
  top <- max(values)
  spread <- max(values) - min(values)
  if (spread == 0) spread <- 1
  spans <- lapply(comparisons, function(comparison) match(comparison[1:2], names) - 1)
  levels <- bracket_levels(spans)
  colour <- settings$neutral$muted
  layers <- list()
  for (index in seq_along(spans)) {
    span <- spans[[index]]
    y <- top + spread * rules$bracket_step * (levels[index] + 1)
    tick <- spread * rules$bracket_tick
    path <- ggplot2::geom_path(data = data.frame(x = span[c(1, 1, 2, 2)], y = c(y - tick, y, y, y - tick)),
                               ggplot2::aes(.data$x, .data$y), colour = colour, inherit.aes = FALSE,
                               linewidth = pt_to_linewidth(hl_tokens()$reference$width * settings$base_size))
    path$hairline_secondary <- TRUE
    path$hairline_fixed <- TRUE
    label <- ggplot2::annotate("text", x = mean(span), y = y, label = comparisons[[index]][3], vjust = -0.35,
                               colour = colour, family = settings$font, size = role_size(settings, "label") /
                                 ggplot2::.pt)
    headroom <- ggplot2::geom_blank(data = data.frame(x = span[1], y = y + spread * rules$bracket_step * 0.6),
                                    ggplot2::aes(.data$x, .data$y), inherit.aes = FALSE)
    layers <- c(layers, list(path, label, headroom))
  }
  layers
}

resolve_comparisons <- function(comparisons, data, group, value, names) {
  if (is.character(comparisons) && length(comparisons) == 1 && comparisons %in% c("all", "adjacent")) {
    pairs <- utils::combn(names, 2, simplify = FALSE)
    if (comparisons == "adjacent") pairs <- Filter(function(pair) abs(diff(match(pair, names))) == 1, pairs)
    comparisons <- pairs
  } else if (is.character(comparisons) && length(comparisons) == 1) {
    stop(sprintf("hairline: raincloud: comparisons '%s' must be 'all', 'adjacent' or a list", comparisons),
         call. = FALSE)
  }
  lapply(comparisons, function(pair) {
    if (length(pair) == 3) return(pair)
    for (name in pair) {
      if (!name %in% names) {
        stop(sprintf("hairline: raincloud: comparison group '%s' is not one of: %s", name,
                     paste(names, collapse = ", ")), call. = FALSE)
      }
    }
    values <- lapply(pair, function(name) data[[value]][as.character(data[[group]]) == name])
    c(pair, format_p(rank_sum_p(values[[1]], values[[2]])))
  })
}

#' Raincloud plot
#'
#' Per group a half density, the box (interquartile range and median) and
#' the points, with "n = …" under the group names. Comparison brackets show
#' your test results and are stacked so they never overlap.
#'
#' @param data A data frame.
#' @param group,value Columns: the grouping and the measurement; or a formula `value ~ group` as `group`.
#' @param title,subtitle,caption Frame texts.
#' @param y_title Axis title above the y-axis.
#' @param order Group order.
#' @param comparisons `"all"` or `"adjacent"` pairs, or a list of `c(group, group)` pairs (Wilcoxon rank-sum p
#'   computed) or `c(group, group, text)` with your own result.
#' @param colors Named colours for this chart only, e.g. `c(Male = "#2474cf")`; they override the colour set
#'   for the number of groups and are not remembered for other charts.
#' @return A ggplot with the hairline frame.
#' @export
hl_raincloud <- function(data, group, value = NULL, title = NULL, subtitle = NULL, caption = NULL, y_title = NULL,
                         order = NULL, comparisons = list(), colors = NULL) {
  if (inherits(group, "formula")) {
    sides <- formula_sides(group)
    value <- deparse(sides$left)
    group <- sides$right[1]
  }
  check_columns(data, c(group, value))
  names <- order %||% unique(as.character(data[[group]]))
  title <- title %||% paste(humanise(value), "by", gsub("_", " ", group))
  comparisons <- resolve_comparisons(comparisons, data, group, value, names)
  for (name in unlist(lapply(comparisons, `[`, 1:2))) {
    if (!name %in% names) {
      stop(sprintf("hairline: raincloud: comparison group '%s' is not one of: %s", name,
                   paste(names, collapse = ", ")), call. = FALSE)
    }
  }
  rules <- hl_tokens()$raincloud
  plot <- ggplot2::ggplot()
  counts <- character()
  palette <- colours_for(names, colors)
  for (index in seq_along(names)) {
    values <- data[[value]][as.character(data[[group]]) == names[index]]
    plot <- plot + raincloud_group_layers(values, index - 1, palette[[names[index]]], rules)
    counts[index] <- paste("n =", length(values))
  }
  plot <- plot + raincloud_bracket_layers(comparisons, names, data[[value]], rules) +
    ggplot2::scale_x_continuous(breaks = seq_along(names) - 1, labels = names, limits = c(-0.6, length(names) - 0.4),
                                expand = c(0, 0)) +
    ggplot2::labs(title = title, subtitle = subtitle, caption = caption, x = NULL, y = y_title) + theme_hairline() +
    hl_legend(list())
  plot@meta$hairline_table <- list(heading = NULL, rows = list(list(label = "", colour = NULL,
                                                                    x = seq_along(names) - 1, text = counts)))
  plot
}
