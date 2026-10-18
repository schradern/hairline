# Bar chart, mirroring the Python bars(): counts or sums per category, side by side or stacked, vertical or
# horizontal, values at the bar ends.

bar_table <- function(data, category, value, by, order, sort) {
  keys <- if (is.null(by)) as.character(data[[category]]) else
    paste(data[[category]], data[[by]], sep = "\r")
  first <- !duplicated(keys)
  table <- data[first, c(category, by), drop = FALSE]
  table[[category]] <- as.character(table[[category]])
  table$.value <- as.numeric(tapply(data[[value]], factor(keys, levels = unique(keys)), sum))
  names <- order %||% unique(table[[category]])
  if (identical(sort, "value") && is.null(order)) {
    totals <- tapply(table$.value, table[[category]], sum)
    names <- names[order(-totals[names], seq_along(names))]
  }
  groups <- if (is.null(by)) "" else unique(as.character(table[[by]]))
  list(table = table, names = names, groups = groups)
}

bars_horizontal <- function(names) {
  rules <- hl_tokens()$bars
  length(names) > rules$horizontal_count || max(nchar(names)) > rules$horizontal_length
}

bar_frame <- function(parts, category, by, horizontal, percent) {
  table <- parts$table
  if (percent) table$.value <- table$.value / stats::ave(table$.value, table[[category]], FUN = sum)
  levels <- if (horizontal) rev(parts$names) else parts$names
  data.frame(category = factor(table[[category]], levels = levels),
             group = factor(if (is.null(by)) "" else as.character(table[[by]]), levels = parts$groups),
             value = table$.value,
             label = if (percent) vapply(table$.value, hl_format_percent, character(1), digits = 0) else
               vapply(table$.value, hl_format_number, character(1), digits = 0))
}

bar_value_mapping <- function(horizontal) {
  if (horizontal) {
    ggplot2::aes(.data$value, .data$category, label = .data$label, group = .data$group)
  } else {
    ggplot2::aes(.data$category, .data$value, label = .data$label, group = .data$group)
  }
}

bar_text <- function(mapping, frame, position, colour, settings, ...) {
  ggplot2::geom_text(mapping, data = frame, position = position, colour = colour, family = settings$font,
                     size = role_size(settings, "label") / ggplot2::.pt, ...)
}

stacked_text_layers <- function(frame, colours, horizontal, percent) {
  rules <- hl_tokens()$bars
  settings <- hl_settings()
  largest <- if (percent) 1 else max(tapply(frame$value, frame$category, sum))
  shown <- frame
  shown$label[shown$value < rules$segment_min * largest | shown$value <= 0] <- ""
  style <- list(neutral = settings$neutral)
  inks <- vapply(as.character(shown$group), function(name) contrast_text(colours[[name]], style), character(1))
  layers <- list(bar_text(bar_value_mapping(horizontal), shown, ggplot2::position_stack(vjust = 0.5, reverse = TRUE),
                          inks, settings))
  if (!percent) {
    totals <- stats::aggregate(frame$value, list(category = frame$category), sum)
    totals <- data.frame(category = totals$category, value = totals$x, group = "",
                         label = vapply(totals$x, hl_format_number, character(1), digits = 0))
    gap <- rules$label_gap
    layers[[2]] <- bar_text(bar_value_mapping(horizontal), totals, "identity", settings$neutral$muted, settings,
                            hjust = if (horizontal) -gap else 0.5, vjust = if (horizontal) 0.5 else -gap)
  }
  layers
}

# Groups side by side; horizontal bars run top-down in legend order.
bar_dodge <- function(horizontal) ggplot2::position_dodge(width = hl_tokens()$bars$width, reverse = horizontal)

# Room on the value axis for the labels at the bar ends.
bar_headroom <- function(frame, horizontal, percent, stacked) {
  if (stacked && percent) return(list())
  largest <- if (stacked) max(tapply(frame$value, frame$category, sum), na.rm = TRUE) else max(frame$value)
  reach <- data.frame(category = factor(levels(frame$category)[1], levels = levels(frame$category)),
                      value = largest * (1 + hl_tokens()$bars$label_headroom))
  mapping <- if (horizontal) ggplot2::aes(.data$value, .data$category) else ggplot2::aes(.data$category, .data$value)
  list(ggplot2::geom_blank(mapping, data = reach, inherit.aes = FALSE))
}

# Space before the first and after the last category, as in Python.
bar_category_scale <- function(horizontal) {
  expand <- ggplot2::expansion(add = hl_tokens()$bars$category_pad)
  if (horizontal) ggplot2::scale_y_discrete(expand = expand) else ggplot2::scale_x_discrete(expand = expand)
}

bar_layers <- function(frame, colours, horizontal, stacked, labels, percent) {
  rules <- hl_tokens()$bars
  settings <- hl_settings()
  position <- if (stacked) ggplot2::position_stack(reverse = TRUE) else bar_dodge(horizontal)
  mapping <- if (horizontal) ggplot2::aes(.data$value, .data$category, fill = .data$group) else
    ggplot2::aes(.data$category, .data$value, fill = .data$group)
  edge <- if (stacked) list(colour = settings$neutral$surface, linewidth = pt_to_linewidth(rules$gap_pt / 2)) else
    list(colour = NA)
  layers <- list(do.call(ggplot2::geom_col, c(list(mapping, data = frame, position = position,
                                                   width = rules$width * 0.92,
                                                   orientation = if (horizontal) "y" else "x"), edge)),
                 ggplot2::scale_fill_manual(values = colours, guide = if (length(colours) > 1) "legend" else "none"))
  if (!labels) return(layers)
  if (stacked) {
    return(c(layers, stacked_text_layers(frame, colours, horizontal, percent),
             bar_headroom(frame, horizontal, percent, TRUE)))
  }
  gap <- rules$label_gap
  c(layers, bar_headroom(frame, horizontal, percent, FALSE),
    list(bar_text(bar_value_mapping(horizontal), frame, bar_dodge(horizontal),
                  settings$neutral$muted, settings, hjust = if (horizontal) -gap else 0.5,
                  vjust = if (horizontal) 0.5 else -gap)))
}

#' Bar chart
#'
#' Bars per category; without `value` the rows are counted. Long or many
#' labels turn the bars horizontal; a single series is sorted by value unless
#' `order` or `sort = "given"` says otherwise. Values sit at the bar ends.
#'
#' @param data A data frame.
#' @param category Column with the categories.
#' @param value Column with the amounts; `NULL` counts rows.
#' @param by Grouping column; groups side by side, or stacked with `stacked = TRUE`.
#' @param title,subtitle,caption Frame texts; the title defaults to the columns.
#' @param stacked Stack the groups.
#' @param percent Show shares of each category instead of amounts.
#' @param horizontal Force horizontal (`TRUE`) or vertical (`FALSE`) bars.
#' @param sort `"value"` or `"given"`; default by value, except for groups side by side.
#' @param order Category order.
#' @param labels Print the values: at the bar ends, or inside stacked segments with the totals at the ends.
#' @param colors Named colours for this chart only, e.g. `c(Male = "#2474cf")`; they override the colour set
#'   for the number of groups and are not remembered for other charts.
#' @return A ggplot with the hairline frame.
#' @export
hl_bars <- function(data, category, value = NULL, by = NULL, title = NULL, subtitle = NULL, caption = NULL,
                    stacked = FALSE, percent = FALSE, horizontal = NULL, sort = NULL, order = NULL, labels = TRUE,
                    colors = NULL) {
  counted <- with_counts(data, value)
  check_columns(counted$data, c(category, counted$value, by))
  parts <- bar_table(counted$data, category, counted$value, by, order,
                     sort %||% if (is.null(by) || stacked) "value" else "given")
  horizontal <- horizontal %||% bars_horizontal(parts$names)
  colours <- if (is.null(by)) stats::setNames(lone_colour(), "") else
    colours_for(parts$groups, colors)
  plot <- ggplot2::ggplot() +
    bar_layers(bar_frame(parts, category, by, horizontal, percent), colours, horizontal, stacked, labels, percent) +
    ggplot2::labs(title = title %||% paste(humanise(counted$value), "by", gsub("_", " ", category)),
                  subtitle = subtitle, caption = caption, x = NULL, y = NULL) + theme_hairline() +
    bar_category_scale(horizontal)
  if (percent) plot <- plot + if (horizontal) scale_x_hairline(percent = TRUE) else scale_y_hairline(percent = TRUE)
  plot
}
