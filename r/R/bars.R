# Bar chart, mirroring the Python bars(): counts or sums per category, side by side or stacked, vertical or
# horizontal, values at the bar ends.

bar_table <- function(data, category, value, by, order, sort) {
  if (!sort %in% c("value", "given")) {
    stop(sprintf("hairline: bars: sort '%s' must be 'value' or 'given'", sort), call. = FALSE)
  }
  check_labels(data, c(category, by), "bars")
  check_present(data, value, "bars")
  names <- ordered_names(data[[category]], order, "bars", category)
  groups <- if (is.null(by)) "" else group_names(data[[by]])
  keys <- if (is.null(by)) as.character(data[[category]]) else
    combination_key(data[[category]], data[[by]])
  first <- !duplicated(keys)
  table <- data[first, c(category, by), drop = FALSE]
  table[[category]] <- as.character(table[[category]])
  table$.value <- as.numeric(tapply(data[[value]], factor(keys, levels = unique(keys)), sum, na.rm = TRUE))
  # Categories left out of `order` are not drawn.
  table <- table[table[[category]] %in% names, , drop = FALSE]
  if (identical(sort, "value") && is.null(order)) {
    totals <- tapply(table$.value, table[[category]], sum)
    names <- names[order(-totals[names], seq_along(names))]
  }
  list(table = table, names = names, groups = groups)
}

bars_horizontal <- function(names) {
  rules <- hl_tokens()$bars
  length(names) > rules$horizontal_count || max(nchar(names)) > rules$horizontal_length
}

bar_frame <- function(parts, category, by, horizontal, percent) {
  table <- parts$table
  digits <- auto_digits(table$.value)
  if (percent) {
    totals <- stats::ave(table$.value, table[[category]], FUN = sum)
    empty <- table[[category]][!(totals > 0)]
    if (length(empty)) {
      stop(sprintf(paste("hairline: bars: percent needs a total above zero in every category; '%s' totals %s,",
                         "so its shares are undefined"), empty[1], format(totals[!(totals > 0)][1])), call. = FALSE)
    }
    table$.value <- table$.value / totals
  }
  levels <- if (horizontal) rev(parts$names) else parts$names
  # A bar's value: whole percentages, or the data's own decimals (0.12 stays 0.12, counts stay whole).
  frame <- data.frame(category = factor(table[[category]], levels = levels),
                      group = factor(if (is.null(by)) "" else as.character(table[[by]]), levels = parts$groups),
                      value = table$.value,
                      label = if (percent) vapply(table$.value, hl_format_percent, character(1), digits = 0) else
                        vapply(table$.value, hl_format_number, character(1), digits = digits))
  attr(frame, "digits") <- digits
  frame
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
  largest <- if (percent) 1 else max(tapply(pmax(frame$value, 0), frame$category, sum), na.rm = TRUE)
  shown <- frame
  shown$label[shown$value < rules$segment_min * largest | shown$value <= 0] <- ""
  style <- list(neutral = settings$neutral)
  inks <- vapply(as.character(shown$group), function(name) contrast_text(colours[[name]], style), character(1))
  layers <- list(bar_text(bar_value_mapping(horizontal), shown, ggplot2::position_stack(vjust = 0.5, reverse = TRUE),
                          inks, settings))
  if (!percent) {
    ups <- tapply(pmax(frame$value, 0), frame$category, sum)
    downs <- tapply(pmin(frame$value, 0), frame$category, sum)
    present <- !is.na(ups)
    # The signed total at the end of the stack: past the positive segments, or the negative ones if none is positive.
    totals <- data.frame(category = factor(names(ups)[present], levels = levels(frame$category)),
                         value = ifelse(ups > 0, ups, downs)[present], group = "",
                         label = vapply((ups + downs)[present], hl_format_number, character(1),
                                        digits = attr(frame, "digits") %||% 0))
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
  largest <- if (stacked) max(tapply(pmax(frame$value, 0), frame$category, sum), na.rm = TRUE) else max(frame$value)
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

# "Count by unit", or "Count by unit and sex" when bars are split by a second column.
bars_title <- function(value, category, by) {
  split <- if (!is.null(by) && !identical(by, category)) paste(" and", gsub("_", " ", by)) else ""
  paste0(humanise(value), " by ", gsub("_", " ", category), split)
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
#' @param colors Named colours for this chart only, e.g. `c(Male = "#0a6ddd")`; they override the colour set
#'   for the number of groups and are not remembered for other charts.
#' @return A ggplot with the hairline frame.
#' @examples
#' admissions <- data.frame(
#'   diagnosis = c("Sepsis", "Sepsis", "Trauma", "Cardiac", "Cardiac", "Cardiac"),
#'   sex = c("Female", "Male", "Male", "Female", "Male", "Male"))
#' hl_bars(admissions, "diagnosis")
#' hl_bars(admissions, "diagnosis", by = "sex", stacked = TRUE)
#' @export
hl_bars <- function(data, category, value = NULL, by = NULL, title = NULL, subtitle = NULL, caption = NULL,
                    stacked = FALSE, percent = FALSE, horizontal = NULL, sort = NULL, order = NULL, labels = TRUE,
                    colors = NULL) {
  counted <- with_counts(data, value)
  check_columns(counted$data, c(category, counted$value, by))
  stacked <- stacked && !is.null(by)
  parts <- bar_table(counted$data, category, counted$value, by, order,
                     sort %||% if (is.null(by) || stacked) "value" else "given")
  horizontal <- horizontal %||% bars_horizontal(parts$names)
  colours <- if (is.null(by)) stats::setNames(lone_colour(), "") else
    colours_for(parts$groups, colors)
  plot <- ggplot2::ggplot() +
    bar_layers(bar_frame(parts, category, by, horizontal, percent), colours, horizontal, stacked, labels, percent) +
    ggplot2::labs(title = title %||% bars_title(counted$value, category, by),
                  subtitle = subtitle, caption = caption, x = NULL, y = NULL) + theme_hairline() +
    bar_category_scale(horizontal)
  if (percent) plot <- plot + if (horizontal) scale_x_hairline(percent = TRUE) else scale_y_hairline(percent = TRUE)
  plot
}
