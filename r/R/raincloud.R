# Raincloud, mirroring the Python raincloud(): per group a half density, the box (IQR and
# median) and the points, with "n = …" under the group names and comparison brackets stacked without overlap.

raincloud_default_summary <- c("median", "iqr")

# Density and points of the values drawn; the summary marks of the values counted, quartiles held within the drawn
# range. Returns the layers and what they draw, for the group's tooltip targets: the marks in data units, where the
# summary tip points and the points. As Python's draw_group().
raincloud_group_layers <- function(values, position, colour, rules, counted = values,
                                   marks = raincloud_default_summary) {
  layers <- list()
  shapes <- list()
  curve <- density_curve(values)
  if (!is.null(curve)) {
    start <- position + rules$density_offset
    outline <- data.frame(x = c(start, start + curve$height / max(curve$height) * rules$density_width, start),
                          y = c(curve$grid[1], curve$grid, curve$grid[length(curve$grid)]))
    layers[[1]] <- ggplot2::geom_polygon(data = outline, ggplot2::aes(.data$x, .data$y), fill = colour,
                                         alpha = rules$density_opacity, colour = NA, inherit.aes = FALSE)
    shapes[[1]] <- list(polygon = as.matrix(outline), alpha = rules$density_opacity)
  }
  points <- data.frame(x = position + rules$points_centre + jitter_offsets(length(values)) * rules$points_spread,
                       y = values)
  summary <- raincloud_summary_layers(counted, range(values), position, colour, marks, rules)
  radius <- hl_tokens()$lines$point_radius * hl_settings()$base_size
  dots <- lapply(seq_len(nrow(points)), function(index) list(dot = c(points$x[index], points$y[index]), r = radius))
  list(layers = c(layers, summary$layers,
                  list(static_layer(ggplot2::geom_point(data = points, ggplot2::aes(.data$x, .data$y), colour = colour,
                                                        inherit.aes = FALSE)))),
       marks = c(shapes, summary$marks, dots), at = c(position, summary$top), points = points)
}

# A vertical segment at the box's place, kept out of light slots, line thinning and tooltips.
raincloud_segment <- function(x, y, x_end, y_end, colour, width) {
  layer <- ggplot2::geom_segment(data = data.frame(x = x, y = y, xend = x_end, yend = y_end),
                                 ggplot2::aes(.data$x, .data$y, xend = .data$xend, yend = .data$yend),
                                 colour = colour, lineend = "butt", inherit.aes = FALSE,
                                 linewidth = pt_to_linewidth(width))
  layer$hairline_secondary <- TRUE
  layer$hairline_fixed <- TRUE
  layer
}

raincloud_bar <- function(position, half, ends, colour) {
  ggplot2::geom_rect(data = data.frame(xmin = position - half, xmax = position + half, ymin = ends[1],
                                       ymax = ends[2]),
                     ggplot2::aes(xmin = .data$xmin, xmax = .data$xmax, ymin = .data$ymin, ymax = .data$ymax),
                     fill = colour, colour = NA, inherit.aes = FALSE)
}

# At the box's place: the range as a thin line, the IQR as the box or an SD or CI as a slim bar, the median as a
# tick across it (in the surface colour on the box) and the mean as an open diamond. As Python's draw_summary().
# Also returns those marks in data units, for the tooltip targets, and where the summary tip points: the top of the
# bar, else the centre mark, else the top of the range; so hovering the box reads the summary, not a point beside it.
raincloud_summary_layers <- function(counted, drawn, position, colour, marks, rules) {
  settings <- hl_settings()
  tokens <- hl_tokens()
  found <- summary_values(counted)
  held <- function(value) min(max(value, drawn[1]), drawn[2])
  half <- rules$box_half
  width <- tokens$lines$data * settings$base_size
  layers <- list()
  shapes <- list()
  anchors <- list()
  if ("range" %in% marks) {
    line <- tokens$reference$width * settings$base_size
    ends <- c(held(found$low), held(found$high))
    layers <- c(layers, list(raincloud_segment(position, ends[1], position, ends[2], settings$neutral$faint, line)))
    shapes <- c(shapes, list(list(line = cbind(position, ends), width = line, color = settings$neutral$faint)))
    anchors$range <- ends[2]
  }
  bar <- intersect(marks, summary_bars)
  box <- NULL
  if (identical(bar, "iqr")) {
    box <- c(position - half, held(found$q1), position + half, held(found$q3))
  } else if (length(bar) && is.finite(found$sd)) {
    slim <- half * tokens$summary$thin_bar
    ends <- interval_of(found, bar)
    box <- c(position - slim, ends[1], position + slim, ends[2])
  }
  if (!is.null(box)) {
    layers <- c(layers, list(raincloud_bar(position, (box[3] - box[1]) / 2, box[c(2, 4)], colour)))
    shapes <- c(shapes, list(list(rect = box)))
    anchors$bar <- box[4]
  }
  if ("median" %in% marks) {
    tick <- if (identical(bar, "iqr")) settings$neutral$surface else colour
    middle <- held(found$median)
    layers <- c(layers, list(raincloud_segment(position - half, middle, position + half, middle, tick, width)))
    shapes <- c(shapes, list(list(line = cbind(c(position - half, position + half), middle), width = width,
                                  color = tick)))
    anchors$median <- middle
  }
  if ("mean" %in% marks) {
    centre <- held(found$mean)
    layers <- c(layers, list(mean_diamond(position, centre, colour)))
    shapes <- c(shapes, list(list(diamond = c(position, centre),
                                  r = diamond_size * tokens$lines$point_radius * settings$base_size,
                                  color = settings$neutral$surface, edge = colour, edge_width = width * open_edge)))
    anchors$mean <- centre
  }
  first <- intersect(c("bar", "median", "mean", "range"), names(anchors))
  list(layers = layers, marks = shapes, top = if (length(first)) anchors[[first[1]]] else drawn[2])
}

# The mean as an open diamond on a ggplot panel: its half-diagonal `diamond_size` point radii, its outline
# `open_edge` of the data line, as the Python marker "D" and spread's diamond. R draws pch 23 with a half-diagonal
# of 0.375 * 1.25331 of its font size.
mean_diamond <- function(x, y, colour) {
  settings <- hl_settings()
  lines <- hl_tokens()$lines
  edge <- lines$data * settings$base_size * open_edge
  stroke <- 2 * edge / 0.75 / ggplot2::.stroke
  fontsize <- diamond_size * lines$point_radius * settings$base_size / (0.375 * 1.25331)
  layer <- ggplot2::geom_point(data = data.frame(x = x, y = y), ggplot2::aes(.data$x, .data$y), shape = 23,
                               fill = settings$neutral$surface, colour = colour, stroke = stroke,
                               size = (fontsize - stroke * ggplot2::.stroke / 2) / ggplot2::.pt, inherit.aes = FALSE)
  layer$hairline_secondary <- TRUE
  layer$hairline_fixed <- TRUE
  layer
}

# One panel's groups at their positions (a group without values here is left empty) and its comparisons, tested on
# this panel's values: the layers and the bracket levels. As Python's draw_panel().
raincloud_panel_layers <- function(drawn, counted, comparisons, names, palette,
                                   marks = raincloud_default_summary) {
  rules <- hl_tokens()$raincloud
  layers <- list()
  groups <- list()
  for (index in seq_along(names)) {
    if (!length(drawn[[index]])) next
    group <- raincloud_group_layers(drawn[[index]], index - 1, palette[[names[index]]], rules, counted[[index]],
                                    marks)
    layers <- c(layers, group$layers)
    groups[[names[index]]] <- group
  }
  present <- lengths(counted) > 0
  rows <- data.frame(group = rep(names[present], lengths(counted[present])),
                     value = unlist(counted[present], use.names = FALSE))
  pairs <- resolve_comparisons(comparisons, rows, "group", "value", names[present])
  for (name in unlist(lapply(pairs, `[`, 1:2))) {
    if (!name %in% names[present]) {
      stop(sprintf("hairline: raincloud: comparison group '%s' is not one of: %s", name,
                   paste(names[present], collapse = ", ")), call. = FALSE)
    }
  }
  spans <- lapply(pairs, function(pair) match(pair[1:2], names) - 1)
  list(layers = c(layers, raincloud_bracket_layers(pairs, names, unlist(drawn, use.names = FALSE), rules)),
       levels = if (length(spans)) max(bracket_levels(spans)) + 1 else 0, groups = groups)
}

# Each group's tooltip targets on panel `panel`: its summary tip first (the one a keyboard focus shows), then a value
# per point; its density, summary marks and points stay in colour while it is hovered. As Python's group_targets().
raincloud_targets <- function(panel, groups, tips, palette) {
  lapply(names(groups), function(name) {
    group <- groups[[name]]
    summary <- if (!is.null(tips[[name]])) list(list(at = group$at, text = tips[[name]])) else list()
    points <- lapply(seq_len(nrow(group$points)), function(index) {
      list(at = c(group$points$x[index], group$points$y[index]), value = group$points$y[index])
    })
    chart_target(panel, name, palette[[name]], group$marks, c(summary, points))
  })
}

bracket_headroom <- 0.6 # bracket steps above the highest bracket, for its label

# The least plot height (x the base size) at which each of `levels` bracket levels has room for its p label: the
# label (pad, cap height and descender at the label size) above its bracket and clear of the next bracket's ticks, on
# a value axis spanning the data and the brackets, with room for the ticks' overshoot. NULL without brackets; never
# below `spacing.min_plot_height`.
bracket_plot_height <- function(levels) {
  if (!levels) return(NULL)
  tokens <- hl_tokens()
  metrics <- font_metrics()
  rules <- tokens$raincloud
  label <- tokens$type$roles$label$factor * (rules$label_pad + metrics$cap_height + metrics$descender)
  level <- label / (1 - rules$bracket_tick / rules$bracket_step)
  steps <- 1 / rules$bracket_step + levels + bracket_headroom
  overshoot <- 1 + tokens$ticks$overshoot_low + tokens$ticks$overshoot_high
  max(tokens$spacing$min_plot_height, level * steps * overshoot)
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
    headroom <- ggplot2::geom_blank(data = data.frame(x = span[1], y = y + spread * rules$bracket_step *
                                                        bracket_headroom),
                                    ggplot2::aes(.data$x, .data$y), inherit.aes = FALSE)
    layers <- c(layers, list(path, label, headroom))
  }
  layers
}

resolve_comparisons <- function(comparisons, data, group, value, names) {
  if (is.character(comparisons) && length(comparisons) == 1 && comparisons %in% c("all", "adjacent")) {
    pairs <- if (length(names) > 1) utils::combn(names, 2, simplify = FALSE) else list()
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
#' your test results and are stacked so they never overlap. Missing values
#' are left out, and "n = …" counts the values shown.
#'
#' @param data A data frame.
#' @param group,value Columns: the grouping and the measurement; or a formula `value ~ group` as `group`.
#' @param title,subtitle,caption Frame texts.
#' @param y_title Axis title above the y-axis.
#' @param order Group order.
#' @param comparisons `"all"` or `"adjacent"` pairs, or a list of `c(group, group)` pairs (Wilcoxon rank-sum p
#'   computed) or `c(group, group, text)` with your own result.
#' @param colors Named colours for this chart only, e.g. `c(Male = "#0a6ddd")`; they override the colour set
#'   for the number of groups and are not remembered for other charts.
#'   A ramp name such as `"blues"` colours ordered groups light to dark, in the chart's order.
#' @param min_n,clip,clip_stats,color_by,dimension As in [hl_spread()]: groups too small and values clipped off are
#'   named in the caption; "n = …" counts the values the statistics use.
#' @param show_n Write "n = …" under each group.
#' @param columns Panels per row with `facet` (two by default).
#' @param summary The marks at the box's place: any of `"median"` (a tick), `"mean"` (an open diamond), `"iqr"`
#'   (the box), `"range"` (a thin line), `"sd"` and `"ci"` (the mean's SD or 95% CI as a slim bar); one bar at
#'   most. The default is `c("median", "iqr")`; a summary you give is named in the legend.
#' @param stats The same measures as rows of numbers under the groups: any of `"median"`, `"mean"`, `"iqr"`,
#'   `"range"`, `"sd"`, `"ci"`.
#' @param compare Rows with each group's difference against one group or the group to its left (`"adjacent"`),
#'   its 95% CI and p; the caption names the test, which follows the centre as in [hl_spread()].
#' @inheritParams chart_option_params
#' @return A ggplot with the hairline frame.
#' @examples
#' set.seed(1)
#' stays <- data.frame(unit = rep(c("Surgical", "Medical"), each = 30),
#'                     days = round(stats::rexp(60, 0.2), 1))
#' hl_raincloud(stays, "unit", "days", y_title = "Days")
#' @export
hl_raincloud <- function(data, group, value = NULL, title = NULL, subtitle = NULL, caption = NULL, y_title = NULL,
                         order = NULL, comparisons = list(), colors = NULL, min_n = NULL, clip = NULL,
                         clip_stats = FALSE, color_by = NULL, dimension = NULL, sort = NULL, percent = FALSE,
                         show_n = TRUE, x_title = NULL, reference = NULL, highlight = NULL, key_title = NULL,
                         facet = NULL, columns = NULL, summary = NULL, stats = character(), compare = NULL) {
  if (inherits(group, "formula")) {
    sides <- formula_sides(group)
    value <- deparse(sides$left)
    group <- sides$right[1]
  }
  check_columns(data, c(group, value, color_by, facet))
  marks <- if (is.null(summary)) raincloud_default_summary else check_summary(summary, "raincloud")
  stats <- raincloud_check_stats(stats, facet)
  check_present(data, value, "raincloud")
  check_numeric(data, value, "raincloud")
  data <- data[!is.na(data[[value]]), , drop = FALSE]
  names <- chart_groups(data, group, order, "raincloud")
  groups <- stats::setNames(lapply(names, function(name) data[[value]][as.character(data[[group]]) == name]), names)
  dropped <- drop_small(groups, min_n, "raincloud")
  groups <- dropped$groups[sorted_names(names(dropped$groups), function(name) dropped$groups[[name]], sort,
                                        "raincloud")]
  names <- names(groups)
  limits <- clip_limits(unlist(groups, use.names = FALSE), clip, "raincloud")
  drawn <- lapply(groups, within_limits, limits = limits)
  counted <- if (clip_stats) drawn else groups
  title <- title %||% paste(humanise(value), "by", gsub("_", " ", group))
  coloured <- series_colours(names, data, group, color_by, colors, dimension, "raincloud", highlight,
                             named = TRUE)
  panels <- if (is.null(facet)) "" else chart_groups(data, facet, NULL, "raincloud")
  plot <- ggplot2::ggplot()
  levels <- 0
  compared <- raincloud_compare_rows(counted, compare, facet, marks, percent)
  every_counted <- unlist(counted, use.names = FALSE)
  targets <- list()
  for (panel in panels) {
    here <- if (is.null(facet)) rep(TRUE, nrow(data)) else as.character(data[[facet]]) == panel
    values <- lapply(names, function(name) data[[value]][here & as.character(data[[group]]) == name])
    shown <- lapply(values, within_limits, limits = limits)
    built <- raincloud_panel_layers(shown, if (clip_stats) shown else values, comparisons, names, coloured$palette,
                                    marks)
    plot <- plot + if (is.null(facet)) built$layers else in_facet(built$layers, panel, panels)
    levels <- max(levels, built$levels)
    tips <- raincloud_group_tips(stats::setNames(if (clip_stats) shown else values, names), every_counted, marks,
                                 stats, compared$pairs, percent)
    targets <- c(targets, raincloud_targets(match(panel, panels), built$groups, tips, coloured$palette))
    if (!is.null(facet)) {
      total <- sum(lengths(if (clip_stats) shown else values))
      plot <- plot + hl_panel_header(panel = panel, name = panel,
                                     stats = if (show_n) c(n = hl_format_number(total, 0)) else NULL)
    }
  }
  counts <- vapply(counted, function(values) word("n_equals", n = hl_format_number(length(values), 0)), character(1))
  notes <- c(dropped$note, if (!is.null(clip)) clip_caption(data[[value]], limits, clip_stats), compared$note)
  plot <- plot +
    ggplot2::scale_x_continuous(breaks = seq_along(names) - 1, labels = names, limits = c(-0.6, length(names) - 0.4),
                                expand = c(0, 0)) +
    ggplot2::labs(title = title, subtitle = subtitle, caption = with_caption(caption, notes), x = NULL,
                  y = y_title) + theme_hairline() +
    hl_legend(c(if (!is.null(color_by)) coarse_legend(coloured),
                if (!is.null(summary)) summary_legend(marks, "line", hl_settings()$neutral$ink)))
  if (!is.null(facet)) {
    plot <- plot + ggplot2::facet_wrap(ggplot2::vars(.data$.facet), ncol = columns %||% min(length(panels), 2))
  }
  table <- if (show_n && is.null(facet)) {
    # Where "n = 20" under each group would meet, the row reads "n" and then the bare counts.
    list(list(label = "", colour = NULL, x = seq_along(names) - 1, text = unname(counts),
              compact = list(label = "n", text = vapply(counted, function(values) hl_format_number(length(values), 0),
                                                        character(1), USE.NAMES = FALSE))))
  }
  table <- c(table, raincloud_stat_rows(counted, stats, percent), compared$rows)
  if (length(table)) plot@meta$hairline_table <- list(heading = NULL, rows = table)
  if (percent) plot <- plot + scale_y_hairline(percent = TRUE)
  # A short plot (one column of a two-column page) would stack the p labels into the brackets above them.
  plot@meta$hairline_min_plot <- bracket_plot_height(levels)
  plot@meta$hairline_targets <- targets
  chart_options(plot, "raincloud", names, x_title = x_title, reference = reference, key_title = key_title)
}
