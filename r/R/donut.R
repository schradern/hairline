# Donut and nested donut: one ring, or up to three hierarchy levels.

donut_totals <- function(data, columns, value) {
  keys <- do.call(paste, c(lapply(columns, function(column) as.character(data[[column]])), sep = "\r"))
  first <- !duplicated(keys)
  sums <- tapply(data[[value]], factor(keys, levels = unique(keys)), sum)
  grouped <- data[first, columns, drop = FALSE]
  grouped[[value]] <- as.numeric(sums)
  for (index in seq_len(nrow(grouped))) {
    if (grouped[[value]][index] < 0) {
      stop(sprintf("hairline: donut: '%s' has a negative value (%s); shares need values of zero or more",
                   paste(unlist(grouped[index, columns]), collapse = " / "), format(grouped[[value]][index])),
           call. = FALSE)
    }
  }
  grouped[grouped[[value]] > 0, , drop = FALSE]
}

donut_segment <- function(name, amount, total, colour, parent, index) {
  share <- amount / total
  list(name = name, value = amount, share = share, share_text = hl_format_percent(share, 0), color = colour,
       parent = parent, index = index)
}

top_ring <- function(data, column, value, fold) {
  grouped <- donut_totals(data, column, value)
  names <- as.character(grouped[[column]])
  amounts <- grouped[[value]]
  folded <- fold && length(names) > hl_tokens()$donut$max_slices
  if (folded) {
    result <- fold_other(names, amounts, hl_tokens()$donut$max_slices)
    names <- result$labels
    amounts <- result$values
  }
  colours <- vapply(if (folded) names[-length(names)] else names, hl_color, character(1), USE.NAMES = FALSE)
  if (folded) colours <- c(colours, hl_tokens()$focus$context)
  lapply(seq_along(names), function(index) {
    donut_segment(names[index], amounts[index], sum(amounts), colours[index], NULL, index - 1L)
  })
}

child_ring <- function(data, levels, value, parents, total) {
  grouped <- donut_totals(data, levels, value)
  ring <- list()
  for (parent in parents) {
    rows <- grouped[as.character(grouped[[levels[length(levels) - 1]]]) == parent$name, , drop = FALSE]
    colours <- tints(parent$color, nrow(rows))
    for (index in seq_len(nrow(rows))) {
      ring[[length(ring) + 1]] <- donut_segment(as.character(rows[[levels[length(levels)]]][index]),
                                                rows[[value]][index], total, colours[index], parent$index,
                                                length(ring))
    }
  }
  ring
}

donut_rings <- function(data, label, value, levels = NULL, chart = "donut") {
  levels <- levels %||% label
  check_columns(data, c(levels, value))
  if (length(levels) > hl_tokens()$donut$max_levels) {
    stop(sprintf("hairline: %s: %d levels given (%s); at most 3 levels fit", chart, length(levels),
                 paste(levels, collapse = ", ")), call. = FALSE)
  }
  rings <- list(top_ring(data, levels[1], value, fold = length(levels) == 1))
  total <- sum(vapply(rings[[1]], `[[`, numeric(1), "value"))
  for (depth in seq_along(levels)[-1]) {
    rings[[depth]] <- child_ring(data, levels[seq_len(depth)], value, rings[[depth - 1]], total)
  }
  rings
}

#' Donut and nested donut
#'
#' One ring with labels outside and leader lines, or up to three hierarchy
#' levels with a hierarchical key; `labels = "ring"` labels the arcs instead.
#' More than seven slices of a single ring fold into "Other". Children use
#' tints of their parent's colour.
#'
#' @param data A data frame.
#' @param label Column naming the slices of a single ring.
#' @param value Column with the amounts.
#' @param levels Up to three hierarchy columns, inner ring first; replaces `label`.
#' @param title,subtitle,caption Frame texts.
#' @param labels `"outside"` (one ring), `"key"` or `"ring"`; `NULL` picks outside for one ring, key otherwise.
#' @param total Show the total in the centre.
#' @param total_label Text under the total, e.g. `"patients"`.
#' @return A ggplot with the hairline frame.
#' @export
hl_donut <- function(data, label = NULL, value, levels = NULL, title, subtitle = NULL, caption = NULL,
                     labels = NULL, total = TRUE, total_label = NULL) {
  rings <- donut_rings(data, label, value, levels)
  mode <- labels %||% if (length(rings) == 1) "outside" else "key"
  if (!mode %in% c("outside", "key", "ring") || (mode == "outside" && length(rings) > 1)) {
    stop(sprintf("hairline: donut: labels '%s' does not fit %d ring(s); use %s", mode, length(rings),
                 if (length(rings) == 1) "outside, key or ring" else "key or ring"), call. = FALSE)
  }
  amount <- hl_format_number(sum(vapply(rings[[1]], `[[`, numeric(1), "value")), 0)
  spec <- list(rings = rings, labels = mode, total = if (isTRUE(total)) amount else NULL, total_label = total_label)
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title, subtitle = subtitle, caption = caption, x = NULL, y = NULL) +
    theme_hairline(axes = FALSE)
  plot@meta$hairline_drawing <- function(box, measure, style) donut_drawing(spec, box, measure, style)
  plot
}
