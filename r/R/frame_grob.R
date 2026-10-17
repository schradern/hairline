# The frame grob: lays out the extracted parts when it is drawn, so it knows the device size.

hl_gtable <- function(table, built) {
  frame <- grid::gTree(parts = frame_parts(table, built), table = table, cl = "hairline_frame")
  attr(frame, "hairline_frame") <- TRUE
  frame
}

column_label_widths <- function(parts) {
  widths <- numeric(parts$columns)
  for (panel in parts$panels) {
    if (inherits(panel$axis_l, "zeroGrob")) next
    width <- grid::convertWidth(grid::grobWidth(panel$axis_l), "pt", valueOnly = TRUE)
    widths[panel$col] <- max(widths[panel$col], width)
  }
  widths
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
       x_title = !is.null(parts$x_title), x_tick_labels = TRUE, y_label_width_pt = texts$column_widths[1],
       column_label_widths = texts$column_widths, x_tick_rows = x_tick_rows(parts))
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

plan_frame <- function(parts, size) {
  settings <- parts$settings
  spacing <- hl_tokens()$spacing
  margin <- spacing$margin * settings$base_size
  usable <- size[1] - 2 * margin
  texts <- list(title = wrap_text(parts$title, role_style(settings, "title"), usable),
                subtitle = wrap_text(parts$subtitle, role_style(settings, "subtitle"), usable),
                caption = wrap_text(parts$caption, role_style(settings, "caption"), usable),
                column_widths = column_label_widths(parts))
  placed <- pack_legend(parts$legend, margin, size[1] - margin, role_style(settings, "label"),
                        settings$base_size, spacing)
  legend_rows <- if (length(placed)) max(vapply(placed, `[[`, numeric(1), "row")) + 1 else 0
  metrics <- font_metrics()
  layout <- compute_frame(frame_spec(parts, texts, size, legend_rows, header_rows(parts, NULL, TRUE)), metrics)
  composed <- compose_all_headers(parts, layout)
  layout <- compute_frame(frame_spec(parts, texts, size, legend_rows, header_rows(parts, composed)), metrics)
  list(layout = layout, texts = texts, placed = placed, composed = compose_all_headers(parts, layout), size = size)
}
