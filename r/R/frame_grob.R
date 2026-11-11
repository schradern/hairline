# The frame grob: lays out the extracted parts when it is drawn, so it knows the device size.

hl_gtable <- function(table, built) {
  parts <- frame_parts(table, built)
  rows <- built@plot@meta$hairline_rows
  if (!is.null(rows)) parts <- composed_parts(parts, rows)
  frame <- grid::gTree(parts = parts, table = table, cl = "hairline_frame")
  attr(frame, "hairline_frame") <- TRUE
  frame
}

# Row-block names: the label size at the key weight, in the block's colour.
block_style <- function(settings, colour = NULL) role_style(settings, "label", hl_tokens()$type$key_weight, colour)

# Room left of a panel's y labels for its row-block names and the gap after them.
block_width <- function(panel, settings) {
  if (!length(panel$blocks)) return(0)
  style <- block_style(settings)
  names <- max(vapply(panel$blocks, function(block) text_width_pt(block$name, style), numeric(1)))
  names + hl_tokens()$lanes$label_gap * settings$base_size
}

# A key number's width: its label in the label style, then its value at the value weight.
side_pair_width <- function(settings, label, value) {
  text_width_pt(paste0(label, " "), role_style(settings, "label")) +
    text_width_pt(value, role_style(settings, "label", hl_tokens()$type$value_weight))
}

# Room right of each column's panels for their numbers column and the gap before it.
side_widths <- function(parts) {
  widths <- numeric(parts$columns)
  gap <- hl_tokens()$spacing$y_labels_plot * parts$settings$base_size
  for (panel in parts$panels) {
    if (!length(panel$side_numbers)) next
    widest <- max(vapply(panel$side_numbers, function(entry) {
      side_pair_width(parts$settings, entry$label, entry$value)
    }, numeric(1)))
    widths[panel$col] <- max(widths[panel$col], widest + gap)
  }
  widths
}

column_label_widths <- function(parts) {
  widths <- numeric(parts$columns)
  for (panel in parts$panels) {
    if (inherits(panel$axis_l, "zeroGrob")) next
    width <- grid::convertWidth(grid::grobWidth(panel$axis_l), "pt", valueOnly = TRUE) +
      block_width(panel, parts$settings)
    widths[panel$col] <- max(widths[panel$col], width)
  }
  widths
}

x_title_rows <- function(parts) {
  rows <- logical(parts$rows)
  for (index in seq_along(parts$panels)) {
    if (!is.null(panel_header_for(parts, index)$x_title)) rows[parts$panels[[index]]$row] <- TRUE
  }
  rows
}

x_tick_rows <- function(parts) {
  rows <- logical(parts$rows)
  for (panel in parts$panels) if (!inherits(panel$axis_b, "zeroGrob")) rows[panel$row] <- TRUE
  rows
}

frame_spec <- function(parts, texts, size, legend_rows, header_lines) {
  settings <- parts$settings
  sizes <- lapply(stats::setNames(nm = names(hl_tokens()$type$roles)), role_size, settings = settings)
  list(width_pt = size[1], height_pt = size[2], base_size = settings$base_size, sizes = sizes,
       title_lines = max(length(texts$title), 1), subtitle_lines = length(texts$subtitle),
       legend_rows = legend_rows, caption_lines = length(texts$caption), panel_rows = parts$rows,
       panel_columns = parts$columns, panel_header_lines = header_lines, y_title = !is.null(parts$y_title),
       x_title = !is.null(parts$x_title), x_tick_labels = !parts$bare, y_labels = !parts$bare,
       table_lines = table_line_count(parts$table),
       y_label_width_pt = if (parts$bare) 0 else texts$column_widths[1],
       column_label_widths = if (parts$bare) numeric(parts$columns) else texts$column_widths,
       x_tick_rows = if (parts$bare) logical(parts$rows) else x_tick_rows(parts), x_title_rows = x_title_rows(parts),
       row_weights = parts$row_weights %||% numeric(), side_widths = side_widths(parts))
}

compose_all_headers <- function(parts, layout) {
  styles <- header_styles(parts$settings)
  gaps <- header_gaps(parts$settings)
  composed <- list()
  for (index in seq_along(parts$panels)) {
    header <- panel_header_for(parts, index)
    if (is.null(header)) next
    box <- layout$panels[[index]]
    left <- if (parts$panels[[index]]$col == 1) layout$left else box[1]
    composed[[as.character(index)]] <- compose_header(header, left, box[1] + box[3], styles, gaps)
  }
  composed
}

header_rows <- function(parts, composed, provisional = FALSE) {
  counts <- integer(parts$rows)
  for (index in seq_along(parts$panels)) {
    if (provisional && is.null(panel_header_for(parts, index))) next
    if (!provisional && is.null(composed[[as.character(index)]])) next
    row <- parts$panels[[index]]$row
    counts[row] <- max(counts[row], if (provisional) 1L else as.integer(composed[[as.character(index)]]$lines))
  }
  counts
}

# The least height in pt the axes panels keep together: the chart's own (plot@meta$hairline_min_plot, x the base
# size) or `spacing.min_plot_height`, and never less than the y labels need to stand apart.
least_plot_height <- function(parts) {
  own <- (parts$min_plot %||% hl_tokens()$spacing$min_plot_height) * parts$settings$base_size
  max(own, label_rows_height(parts))
}

# The plot height at which no two y labels of a panel meet: each label's lines (cap height and descender, with the
# line gap between lines) and `ticks.label_rows_gap` between labels, at the closest pair of labels, for every row of
# panels. As Python's label_rows_height().
label_rows_height <- function(parts) {
  if (isTRUE(parts$bare) || is.null(parts$built)) return(0)
  tokens <- hl_tokens()
  metrics <- font_metrics()
  size <- role_style(parts$settings, "label")$size
  need <- 0
  for (params in parts$built@layout$panel_params) {
    scale <- params$y
    if (is.null(scale) || is.null(scale$breaks)) next
    labels <- tryCatch(as.character(scale$get_labels()), error = function(error) character())
    places <- if (is.numeric(scale$breaks)) as.numeric(scale$breaks) else attr(scale$breaks, "pos") %||%
      seq_along(scale$breaks)
    shown <- !is.na(places) & nzchar(trimws(labels[seq_along(places)]))
    places <- sort(places[shown])
    steps <- diff(places)
    steps <- steps[steps > 0]
    span <- diff(range(scale$continuous_range))
    if (!length(steps) || span <= 0) next
    lines <- max(lengths(strsplit(labels[shown], "\n")))
    pitch <- size * (lines * (metrics$cap_height + metrics$descender) + (lines - 1) * tokens$type$line_gap +
                       tokens$ticks$label_rows_gap)
    need <- max(need, pitch * span / min(steps))
  }
  need * parts$rows
}

# `grow`: a plot with axes gets a taller figure, where needed, until its panels together keep the least plot height,
# so a narrow figure whose title, legend, headers, axis or table would squeeze the plot grows instead. hl_save()
# plans with it to choose the device size; a plot drawn on a device of fixed size keeps that size.
plan_frame <- function(parts, size, grow = FALSE) {
  settings <- parts$settings
  spacing <- hl_tokens()$spacing
  margin <- spacing$margin * settings$base_size
  usable <- size[1] - 2 * margin
  texts <- list(title = wrap_text(parts$title, role_style(settings, "title"), usable),
                subtitle = wrap_text(parts$subtitle, role_style(settings, "subtitle"), usable),
                caption = wrap_text(parts$caption, role_style(settings, "caption"), usable),
                column_widths = column_label_widths(parts))
  texts$column_widths[1] <- max(texts$column_widths[1], table_label_width(parts))
  placed <- pack_legend(parts$legend, margin, size[1] - margin, role_style(settings, "label"),
                        settings$base_size, spacing, ramp_key_items(parts$ramp_key))
  legend_rows <- if (length(placed)) max(vapply(placed, `[[`, numeric(1), "row")) + 1 else 0
  metrics <- font_metrics()
  # The provisional pass only places the headers across; its height merely has to leave the panels room.
  spec <- frame_spec(parts, texts, size, legend_rows, header_rows(parts, NULL, TRUE))
  spec$height_pt <- kept_frame_height(spec, metrics, least_plot_height(parts))
  composed <- compose_all_headers(parts, compute_frame(spec, metrics))
  spec <- frame_spec(parts, texts, size, legend_rows, header_rows(parts, composed))
  if (grow && !parts$bare) spec$height_pt <- kept_frame_height(spec, metrics, least_plot_height(parts))
  layout <- compute_frame(spec, metrics)
  list(layout = layout, texts = texts, placed = placed, composed = compose_all_headers(parts, layout),
       size = c(spec$width_pt, spec$height_pt), shapes = drawing_shapes(parts, layout))
}
