# Pure frame geometry in pt, origin top-left; mirrors python/src/hairline/layout/frame.py.

font_metrics <- function() {
  path <- system.file("fonts", "metrics.json", package = "hairline")
  jsonlite::read_json(path, simplifyVector = TRUE)
}

frame_defaults <- list(title_lines = 1, subtitle_lines = 0, legend_rows = 0, caption_lines = 0, panel_rows = 1,
                       panel_columns = 1, panel_header_lines = integer(), y_title = FALSE, x_title = FALSE,
                       x_tick_labels = TRUE, y_label_width_pt = 0, y_labels = TRUE, table_lines = 0,
                       column_label_widths = numeric(),
                       x_tick_rows = logical())

text_block <- function(size, count, metrics, line_gap) {
  if (count == 0) return(0)
  size * (count * (metrics$cap_height + metrics$descender) + (count - 1) * line_gap)
}

stack_lines <- function(state, size, count) {
  baselines <- numeric()
  for (index in seq_len(count)) {
    if (index > 1) state$y <- state$y + size * state$line_gap
    baselines <- c(baselines, state$y + size * state$metrics$cap_height)
    state$y <- baselines[length(baselines)] + size * state$metrics$descender
  }
  list(state = state, baselines = baselines)
}

stack_rows <- function(state, size, count, gap) {
  height <- size * (state$metrics$cap_height + state$metrics$descender)
  centers <- numeric()
  for (index in seq_len(count)) {
    if (index > 1) state$y <- state$y + gap
    centers <- c(centers, state$y + height / 2)
    state$y <- state$y + height
  }
  list(state = state, centers = centers)
}

inner_tick_band <- function(spec, row, spacing) {
  rows <- unlist(spec$x_tick_rows)
  shows <- row <= length(rows) && isTRUE(rows[row]) && row < spec$panel_rows
  if (shows) spacing$x_tick_labels * spec$sizes$label else 0
}

column_offsets <- function(spec, spacing) {
  widths <- c(unlist(spec$column_label_widths), rep(0, spec$panel_columns))
  offsets <- vapply(seq_len(spec$panel_columns), function(column) {
    if (column == 1 || widths[column] <= 0) 0 else widths[column] + spacing$y_labels_plot * spec$base_size
  }, numeric(1))
  offsets
}

header_line_count <- function(spec, row) {
  lines <- unlist(spec$panel_header_lines)
  if (row <= length(lines)) lines[row] else 0
}

place_header_block <- function(state, spec, layout, spacing) {
  base <- spec$base_size
  state$y <- state$y + spacing$margin * base
  placed <- stack_lines(state, spec$sizes$title, spec$title_lines)
  state <- placed$state
  layout$title_baselines <- placed$baselines
  if (spec$subtitle_lines > 0) {
    state$y <- state$y + spacing$title_subtitle * base
    placed <- stack_lines(state, spec$sizes$subtitle, spec$subtitle_lines)
    state <- placed$state
    layout$subtitle_baselines <- placed$baselines
  }
  if (spec$legend_rows > 0) {
    state$y <- state$y + spacing$header_legend * base
    rows <- stack_rows(state, spec$sizes$label, spec$legend_rows, spacing$legend_rows * base)
    state <- rows$state
    layout$legend_row_centers <- rows$centers
  }
  state$y <- state$y + spacing$legend_content * base
  list(state = state, layout = layout)
}

fixed_row_height <- function(spec, row, spacing, metrics, line_gap) {
  base <- spec$base_size
  height <- 0
  if (header_line_count(spec, row) > 0) {
    height <- height + text_block(spec$sizes$panel, header_line_count(spec, row), metrics, line_gap) +
      spacing$panel_header * base
  }
  if (row == 1 && isTRUE(spec$y_title)) height <- height + text_block(spec$sizes$label, 1, metrics, line_gap) +
    spacing$y_title * base
  if (row > 1) height <- height + spacing$panel_rows * base
  height + inner_tick_band(spec, row, spacing)
}

fixed_bottom_height <- function(spec, spacing, metrics, line_gap) {
  base <- spec$base_size
  height <- if (isTRUE(spec$x_tick_labels)) spacing$x_tick_labels * spec$sizes$label else 0
  if (isTRUE(spec$x_title)) height <- height + spacing$x_title * base + text_block(spec$sizes$label, 1, metrics, 0)
  if (spec$table_lines > 0) {
    height <- height + spacing$table_gap * base + text_block(spec$sizes$label, spec$table_lines, metrics, line_gap)
  }
  if (spec$caption_lines > 0) {
    height <- height + spacing$content_caption * base + text_block(spec$sizes$caption, spec$caption_lines, metrics,
                                                                   line_gap)
  }
  height + spacing$margin * base
}

frame_panel_height <- function(spec, top, spacing, metrics, line_gap) {
  fixed <- sum(vapply(seq_len(spec$panel_rows), fixed_row_height, numeric(1), spec = spec, spacing = spacing,
                      metrics = metrics, line_gap = line_gap))
  available <- spec$height_pt - top - fixed - fixed_bottom_height(spec, spacing, metrics, line_gap)
  height <- available / spec$panel_rows
  if (height < spacing$min_panel_height * spec$base_size) {
    stop(sprintf(paste0("hairline: figure too small: %.0f pt high leaves %.1f pt per panel for %d panel rows; ",
                        "make it taller or use fewer rows"), spec$height_pt, height, as.integer(spec$panel_rows)),
         call. = FALSE)
  }
  height
}
