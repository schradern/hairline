# Partition bars: a hierarchy as stacked rows, children directly under their parent;
# the same algorithm as the Python package's partition_drawing().

partition_lines <- function(segment, room, height, measure, style) {
  pair <- paste(segment$name, segment$share_text)
  if (measure(pair, "label") <= room) return(pair)
  if (measure(segment$name, "label") <= room && 2 * line_height(style, "label") <= height) {
    return(c(segment$name, segment$share_text))
  }
  if (measure(segment$share_text, "label") <= room) segment$share_text else character()
}

partition_label <- function(segment, left, right, top, height, measure, style, rules) {
  pad <- rules$label_pad * style$base
  lines <- partition_lines(segment, right - left - 2 * pad, height - pad, measure, style)
  neutral <- style$neutral
  line <- line_height(style, "label")
  colour <- if (contrast_ratio(segment$color, neutral$ink) >= contrast_ratio(segment$color, neutral$surface)) {
    neutral$ink
  } else {
    neutral$surface
  }
  first <- top + height / 2 - line * (length(lines) - 1) / 2
  lapply(seq_along(lines), function(index) {
    shape_text((left + right) / 2, baseline_for(first + (index - 1) * line, style, "label"), lines[index], "label",
               colour, "center")
  })
}

partition_row <- function(ring, box, top, height, measure, style, rules) {
  bars <- list()
  labels <- list()
  cumulative <- 0
  gap <- rules$gap_pt
  for (segment in ring) {
    start <- cumulative
    end <- cumulative + segment$share
    cumulative <- end
    left <- box[1] + box[3] * start + if (start > 1e-9) gap / 2 else 0
    right <- box[1] + box[3] * end - if (end < 1 - 1e-9) gap / 2 else 0
    if (right <= left) next
    bars[[length(bars) + 1]] <- list(kind = "polygon", fill = segment$color,
                                     points = rbind(c(left, top), c(right, top), c(right, top + height),
                                                    c(left, top + height)))
    labels <- c(labels, partition_label(segment, left, right, top, height, measure, style, rules))
  }
  list(bars = bars, labels = labels)
}

partition_drawing <- function(spec, box, measure, style) {
  rules <- hl_tokens()$partition
  rings <- spec$rings
  base <- style$base
  heading <- line_height(style, "panel")
  gap <- rules$heading_gap * base
  row_gap <- rules$row_gap * base
  available <- box[4] - length(rings) * (heading + gap) - (length(rings) - 1) * row_gap
  height <- min(available / length(rings), rules$max_bar * base)
  bars <- list()
  texts <- list()
  y <- box[2]
  for (index in seq_along(rings)) {
    texts[[length(texts) + 1]] <- shape_text(box[1], y + style$cap_height * style$sizes$panel, spec$levels[[index]],
                                             "panel", style$neutral$ink)
    top <- y + heading + gap
    row <- partition_row(rings[[index]], box, top, height, measure, style, rules)
    bars <- c(bars, row$bars)
    texts <- c(texts, row$labels)
    y <- top + height + row_gap
  }
  c(bars, texts)
}

#' Partition bars
#'
#' A hierarchy as stacked rows, one per level, children directly under their
#' parent; the documented alternative to a nested donut. Labels sit inside
#' the bars (name and share, else the share, else none); a legend row names
#' the top level.
#'
#' @param data A data frame.
#' @param levels Hierarchy columns, top level first (at most three).
#' @param value Column with the amounts.
#' @param title,subtitle,caption Frame texts.
#' @param level_names Row headings; default the column names.
#' @return A ggplot with the hairline frame.
#' @export
hl_partition <- function(data, levels, value, title, subtitle = NULL, caption = NULL, level_names = NULL) {
  names <- level_names %||% levels
  if (length(names) != length(levels)) {
    stop(sprintf("hairline: partition: %d levels but %d level name(s); give one name per level", length(levels),
                 length(names)), call. = FALSE)
  }
  spec <- list(rings = donut_rings(data, NULL, value, levels, chart = "partition"), levels = as.list(names))
  items <- lapply(spec$rings[[1]], function(segment) {
    list(kind = "square", colour = segment$color, label = segment$name)
  })
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title, subtitle = subtitle, caption = caption, x = NULL, y = NULL) +
    theme_hairline(axes = FALSE) + hl_legend(items)
  plot@meta$hairline_drawing <- function(box, measure, style) partition_drawing(spec, box, measure, style)
  plot
}
