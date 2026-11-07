# Bar options for surveys, mirroring the Python bars(): shares of respondents for multiple-choice answers,
# categories drawn as context, an n column right of the bars, and stacked rows whose segments are named inside.

bar_headers <- c("total", "n")

# Multiple choice: each respondent once per answer, as a share of the respondents of the panel (not of the answers,
# which add up to more than 100 %); and the respondents per panel.
respondent_shares <- function(data, category, facet, respondents) {
  check_columns(data, respondents)
  keys <- c(facet, category)
  check_labels(data, keys, "bars")
  rows <- data[!is.na(data[[respondents]]), , drop = FALSE]
  answer <- do.call(combination_key, lapply(c(respondents, keys), function(column) rows[[column]]))
  rows <- rows[!duplicated(answer), , drop = FALSE]
  panels <- if (is.null(facet)) rep("", nrow(rows)) else as.character(rows[[facet]])
  totals <- tapply(rows[[respondents]], factor(panels, levels = unique(panels)), function(values) {
    length(unique(values))
  })
  cell <- do.call(combination_key, lapply(keys, function(column) rows[[column]]))
  first <- !duplicated(cell)
  shares <- rows[first, keys, drop = FALSE]
  answers <- as.numeric(table(factor(cell, levels = cell[first])))
  shares$.share <- answers / as.numeric(totals[panels[first]])
  list(data = shares, n = as.list(totals))
}

check_bar_survey <- function(show_n, header, inside, context, by, stacked, facet) {
  if (!(isTRUE(show_n) || isFALSE(show_n) || identical(show_n, "column"))) {
    stop("hairline: bars: show_n must be TRUE, FALSE or 'column'", call. = FALSE)
  }
  if (!header %in% bar_headers) {
    stop(sprintf("hairline: bars: header '%s' must be one of %s", header, paste(bar_headers, collapse = ", ")),
         call. = FALSE)
  }
  if (!is.null(inside) && !identical(inside, "name")) {
    stop(sprintf("hairline: bars: inside '%s' must be 'name' or NULL", inside), call. = FALSE)
  }
  if (!is.null(inside) && !(!is.null(by) && stacked)) {
    stop("hairline: bars: inside = 'name' writes the names of stacked groups; give by = and stacked = TRUE",
         call. = FALSE)
  }
  if (!is.null(inside) && !is.null(facet)) {
    stop("hairline: bars: inside = 'name' draws one panel; leave out facet", call. = FALSE)
  }
  if (length(context) && !is.null(by)) {
    stop("hairline: bars: context greys categories of a single series; with by =, use colors =", call. = FALSE)
  }
}

check_respondents <- function(value, by, percent) {
  if (!is.null(value) || !is.null(by) || percent) {
    stop("hairline: bars: respondents counts one answer per row; leave out value, by, percent and normalize",
         call. = FALSE)
  }
}

check_context <- function(context, names) {
  unknown <- setdiff(context, names)
  if (length(unknown)) {
    stop(sprintf("hairline: bars: context names '%s', which is not a category; categories: %s", unknown[1],
                 paste(names, collapse = ", ")), call. = FALSE)
  }
}

# Categories named as context (an exclusive "none" answer), in the context grey, outside the ranking's colour. The
# series layer keeps these bars (transparent) for its tooltips, so their numbers keep the series' decimals; this
# layer only paints them.
context_layer <- function(frame, mapping, position, horizontal, edge) {
  mapping$fill <- NULL
  mapping$alpha <- NULL
  static_layer(do.call(ggplot2::geom_col, c(list(mapping, data = frame, position = position,
                                                 width = hl_tokens()$bars$width * 0.92, fill = context_colour(),
                                                 orientation = if (horizontal) "y" else "x"), edge)))
}

# Each bar's n in a column right of its panel, top row first (horizontal bars).
bar_side_numbers <- function(panels) {
  lapply(panels, function(parts) {
    count <- length(parts$names)
    lapply(seq_along(parts$names), function(index) {
      list(position = count - index + 1, label = "n", value = hl_format_number(parts$n[[parts$names[index]]], 0))
    })
  })
}

# Greys from dark to light, one per position in a row, the near-white step left out.
answer_greys <- function(count) rev(interpolate_colors(hl_ramp("greys"), count + 1))[seq_len(count)]

# Stacked rows whose groups differ per row: one segment per answer, in greys by position (first answer darkest),
# with its name and value for the label inside and the tooltip.
named_segments <- function(parts, category, by, divide, percent) {
  table <- parts$table
  rows <- lapply(parts$names, function(name) table[as.character(table[[category]]) == name, , drop = FALSE])
  colours <- answer_greys(max(vapply(rows, nrow, integer(1))))
  count <- length(parts$names)
  segments <- lapply(seq_along(parts$names), function(index) {
    found <- rows[[index]]
    total <- sum(found$.value, na.rm = TRUE)
    widths <- ifelse(is.na(found$.value) | !(found$.value > 0), 0, found$.value / if (divide) total else 1)
    shown <- vapply(widths, function(width) {
      if (percent) hl_format_percent(width, 0) else format_compact(width, auto_digits(width), NULL)
    }, character(1))
    keep <- widths > 0
    data.frame(name = parts$names[index], group = as.character(found[[by]]), x0 = (cumsum(widths) - widths),
               x1 = cumsum(widths), y = count - index + 1, fill = colours[seq_len(nrow(found))],
               text = shown)[keep, , drop = FALSE]
  })
  do.call(rbind, segments)
}

# The named segments as rectangles on a numeric row axis, their labels and tooltips for the frame.
named_plot <- function(plot, parts, category, by, divide, percent) {
  segments <- named_segments(parts, category, by, divide, percent)
  rules <- hl_tokens()$bars
  settings <- hl_settings()
  half <- rules$width * 0.92 / 2
  pad <- rules$category_pad
  count <- length(parts$names)
  plot <- plot + ggplot2::geom_rect(data = segments, ggplot2::aes(xmin = .data$x0, xmax = .data$x1,
                                                                  ymin = .data$y - half, ymax = .data$y + half,
                                                                  fill = .data$fill),
                                    colour = settings$neutral$surface, linewidth = pt_to_linewidth(rules$gap_pt / 2)) +
    ggplot2::scale_fill_identity() +
    ggplot2::scale_y_continuous(breaks = seq_len(count), labels = rev(parts$labels),
                                limits = c(1 - pad, count + pad), expand = c(0, 0)) + hl_legend(list())
  style <- list(neutral = settings$neutral)
  plot@meta$hairline_inside <- lapply(seq_len(nrow(segments)), function(index) {
    row <- segments[index, ]
    list(panel = 1L, start = row$x0, end = row$x1, y = row$y, text = paste(row$group, row$text),
         colour = contrast_text(row$fill, style))
  })
  plot@meta$hairline_hover <- data.frame(panel = 1L, name = segments$group, colour = segments$fill, x0 = segments$x0,
                                         y0 = segments$y - half, x1 = segments$x1, y1 = segments$y + half,
                                         text = paste0(segments$group, ": ", segments$name, ", ", segments$text))
  plot
}
