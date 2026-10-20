# Spread rows, mirroring the Python spread(): per group the range as a thin line, the interquartile range as a band
# in the group's colour, the median as a dot, an optional reference tick, and the key numbers on the right.

spread_stats <- c("median", "iqr", "mean", "n", "range")
spread_snap_digits <- 10

spread_formatter <- function(values, percent, digits, extra = 0) {
  scale <- if (percent) 100 else 1
  places <- (digits %||% auto_digits(values * scale)) + extra
  suffix <- if (percent) paste0(locale_symbols(NULL)$percent_space, "%") else ""
  function(value) paste0(hl_format_number(round(value * scale, spread_snap_digits), places), suffix)
}

# Key numbers as (label, value) pairs, drawn like a panel header's key numbers.
spread_pairs <- function(values, stats, numbers, mark, mark_label) {
  limits <- density_quantiles(values, c(0, 0.25, 0.5, 0.75, 1))
  number <- numbers[[1]]
  parts <- list(median = c("Median", number(limits[3])),
                iqr = c("IQR", paste0(number(limits[2]), "\u2013", number(limits[4]))),
                mean = c("Mean", numbers[[2]](mean(values))), n = c("n", hl_format_number(length(values), 0)),
                range = c("Range", paste0(number(limits[1]), "\u2013", number(limits[5]))))
  pairs <- unname(parts[stats])
  if (!is.null(mark) && !is.null(mark_label)) pairs[[length(pairs) + 1]] <- c(mark_label, number(mark))
  pairs
}

spread_axis <- function(lows, highs, percent, zero) {
  low <- min(c(lows, if (zero) 0))
  high <- max(c(highs, if (zero) 0))
  breaks <- nice_breaks(low, high)
  limits <- axis_limits(low, high, breaks)
  shown <- round(breaks * if (percent) 100 else 1, spread_snap_digits)
  labels <- vapply(shown, hl_format_number, character(1), digits = forest_decimals(shown))
  if (percent) labels[length(labels)] <- paste0(labels[length(labels)], locale_symbols(NULL)$percent_space, "%")
  list(breaks = breaks, labels = labels, low = limits[1], high = limits[2])
}

spread_spec <- function(data, group, value, order = NULL, marks = NULL, mark_label = NULL,
                        stats = c("median", "iqr", "mean"), percent = FALSE, digits = NULL, zero = FALSE,
                        axis_title = NULL, colors = NULL) {
  check_columns(data, c(group, value))
  unknown <- setdiff(stats, spread_stats)
  if (length(unknown)) {
    stop(sprintf("hairline: spread: unknown statistic '%s'; use any of %s", unknown[1],
                 paste(spread_stats, collapse = ", ")), call. = FALSE)
  }
  check_present(data, value, "spread")
  check_numeric(data, value, "spread")
  names <- chart_groups(data, group, order, "spread")
  samples <- lapply(names, function(name) {
    values <- as.numeric(data[[value]][!is.na(data[[group]]) & as.character(data[[group]]) == name])
    values[!is.na(values)]
  })
  keep <- lengths(samples) > 0
  names <- names[keep]
  samples <- samples[keep]
  every <- unlist(samples)
  whole <- is_whole(every) && !percent
  plain <- spread_formatter(every, percent, digits)
  mean_number <- spread_formatter(every, percent, digits, if (whole) 1 else 0)
  whole <- whole && is.null(digits)
  # Of whole numbers, a quantile between two of them keeps one decimal (a median of 2.5, not 3).
  numbers <- list(function(value) if (quantile_places(value, 0, whole) > 0) mean_number(value) else plain(value),
                  mean_number)
  palette <- colours_for(names, colors)
  rows <- lapply(seq_along(names), function(index) {
    limits <- density_quantiles(samples[[index]], c(0, 0.25, 0.5, 0.75, 1))
    mark <- if (names[index] %in% names(marks)) as.numeric(marks[[names[index]]]) else NULL
    list(name = names[index], color = palette[[names[index]]], low = limits[1], q1 = limits[2], median = limits[3],
         q3 = limits[4], high = limits[5], mark = mark,
         pairs = spread_pairs(samples[[index]], stats, numbers, mark, mark_label))
  })
  marked <- unlist(lapply(rows, `[[`, "mark"))
  list(rows = rows, axis = spread_axis(c(vapply(rows, `[[`, numeric(1), "low"), marked),
                                       c(vapply(rows, `[[`, numeric(1), "high"), marked), percent, zero),
       axis_title = axis_title)
}

spread_row_shapes <- function(row, centre, pitch, scale, style, rules) {
  half <- rules$band * pitch / 2
  band <- rbind(c(scale(row$q1), centre - half), c(scale(row$q3), centre - half), c(scale(row$q3), centre + half),
                c(scale(row$q1), centre + half))
  shapes <- list(list(kind = "line", points = rbind(c(scale(row$low), centre), c(scale(row$high), centre)),
                      color = style$neutral$faint, width = style$leader_width, role = "range"),
                 list(kind = "polygon", points = band, fill = row$color, alpha = rules$band_opacity, role = "band",
                      tip = paste0(row$name, ": ", paste(vapply(row$pairs, paste, character(1), collapse = " "),
                                                         collapse = ", ")),
                      tip_at = c(scale(row$median), centre - half)),
                 forest_marker(scale(row$median), centre, dot_size(style), "dot", row$color))
  if (!is.null(row$mark)) {
    tick <- rules$mark * half
    x <- scale(row$mark)
    shapes[[length(shapes) + 1]] <- list(kind = "line", points = rbind(c(x, centre - tick), c(x, centre + tick)),
                                         color = style$neutral$ink, width = style$leader_width, role = "mark")
  }
  lapply(shapes, function(shape) c(shape, series = row$name))
}

spread_pair_width <- function(pair, measure) {
  measure(paste0(pair[1], " "), "label") + measure(pair[2], "label", hl_tokens()$type$value_weight)
}

# Left edges of the key-number columns, the block ending at `right`: one column per statistic, so labels line up
# from row to row; columns are separated like a panel header's key numbers.
spread_stat_columns <- function(spec, right, measure, style) {
  gap <- hl_tokens()$spacing$stats_pair * style$base
  count <- max(vapply(spec$rows, function(row) length(row$pairs), integer(1)))
  widths <- vapply(seq_len(count), function(index) {
    max(c(0, unlist(lapply(spec$rows, function(row) {
      if (index <= length(row$pairs)) spread_pair_width(row$pairs[[index]], measure)
    }))))
  }, numeric(1))
  start <- right - sum(widths) - gap * (count - 1)
  start + c(0, cumsum(widths + gap))[seq_len(count)]
}

# Label in faint, value in muted at the value weight: the panel header's key-number style.
spread_pair_texts <- function(pairs, lefts, baseline, measure, style) {
  weight <- hl_tokens()$type$value_weight
  unlist(lapply(seq_along(pairs), function(index) {
    label <- paste0(pairs[[index]][1], " ")
    list(shape_text(lefts[index], baseline, label, "label", style$neutral$faint),
         shape_text(lefts[index] + measure(label, "label"), baseline, pairs[[index]][2], "label",
                    style$neutral$muted, "left", weight))
  }), recursive = FALSE)
}

spread_title_shape <- function(spec, right, axis_y, style, rules) {
  if (is.null(spec$axis_title)) return(list())
  size <- style$sizes$label
  ticks <- axis_y + rules$axis_gap * style$base + style$cap_height * size
  baseline <- ticks + style$descender * size + hl_tokens()$spacing$x_title * style$base + style$cap_height * size
  list(c(shape_text(right, baseline, spec$axis_title, "label", style$neutral$muted, "right"), part = "title"))
}

spread_drawing <- function(spec, box, measure, style) {
  rules <- hl_tokens()$spread
  base <- style$base
  size <- style$sizes$label
  gap <- rules$column_gap * base
  lefts <- spread_stat_columns(spec, box[1] + box[3], measure, style)
  left <- box[1] + max(vapply(spec$rows, function(row) measure(row$name, "label"), numeric(1))) + gap
  right <- lefts[1] - gap
  scale <- forest_scale(spec$axis, FALSE, left, right)
  reserve <- rules$axis_gap * base + (style$cap_height + style$descender) * size
  if (!is.null(spec$axis_title)) {
    reserve <- reserve + hl_tokens()$spacing$x_title * base + (style$cap_height + style$descender) * size
  }
  pitch <- min(rules$row_pitch * line_height(style, "label"), (box[4] - reserve) / length(spec$rows))
  bottom <- box[2] + pitch * length(spec$rows)
  shapes <- lapply(spec$axis$breaks, function(value) {
    list(kind = "line", points = rbind(c(scale(value), box[2]), c(scale(value), bottom)), color = style$neutral$grid,
         width = style$grid, role = "grid")
  })
  for (index in seq_along(spec$rows)) {
    row <- spec$rows[[index]]
    centre <- box[2] + pitch * (index - 0.5)
    baseline <- baseline_for(centre, style, "label")
    shapes <- c(shapes, spread_row_shapes(row, centre, pitch, scale, style, rules),
                list(shape_text(box[1], baseline, row$name, "label", style$neutral$ink)),
                spread_pair_texts(row$pairs, lefts, baseline, measure, style))
  }
  axis <- list(axis = spec$axis, favours = NULL, null = NULL)
  c(shapes, forest_axis_shapes(axis, scale, c(left, right), bottom, style, rules),
    spread_title_shape(spec, right, bottom, style, rules))
}

#' Spread rows: distributions per group on one axis
#'
#' Per group, first on top: the range as a thin line, the interquartile range
#' as a band in the group's colour, the median as a dot, an optional reference
#' tick, and the key numbers right-aligned.
#'
#' @param data A data frame.
#' @param group,value Grouping column and numeric column.
#' @param title,subtitle,caption Frame texts; the title defaults to the columns.
#' @param order Group order, top to bottom.
#' @param marks Named reference values per group, e.g. `c("Unit A" = 20)` (a capacity, a target).
#' @param mark_label Name of the reference in the numbers column, e.g. `"beds"`.
#' @param stats Numbers to show: any of `"median"`, `"iqr"`, `"mean"`, `"n"`, `"range"`.
#' @param percent Values are shares (0-1), shown as percentages.
#' @param digits Decimals; default by magnitude (none for whole numbers).
#' @param zero Include zero on the axis.
#' @param axis_title Title under the axis numbers, e.g. the unit.
#' @param colors Named colours for this chart only.
#' @return A ggplot with the hairline frame.
#' @examples
#' set.seed(1)
#' beds <- data.frame(unit = rep(c("Unit A", "Unit B", "Unit C"), each = 50),
#'                    occupied = c(stats::rpois(50, 10), stats::rpois(50, 7), stats::rpois(50, 12)))
#' hl_spread(beds, "unit", "occupied", marks = c("Unit A" = 12, "Unit B" = 8, "Unit C" = 14),
#'           mark_label = "Beds",
#'           zero = TRUE, axis_title = "Occupied beds")
#' @export
hl_spread <- function(data, group, value, title = NULL, subtitle = NULL, caption = NULL, order = NULL, marks = NULL,
                      mark_label = NULL, stats = c("median", "iqr", "mean"), percent = FALSE, digits = NULL,
                      zero = FALSE, axis_title = NULL, colors = NULL) {
  spec <- spread_spec(data, group, value, order, marks, mark_label, stats, percent, digits, zero, axis_title, colors)
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title %||% paste(humanise(value), "by", gsub("_", " ", group)), subtitle = subtitle,
                  caption = caption, x = NULL, y = NULL) + theme_hairline(axes = FALSE)
  plot@meta$hairline_drawing <- function(box, measure, style) spread_drawing(spec, box, measure, style)
  plot@meta$hairline_fit_height <- TRUE
  plot
}
