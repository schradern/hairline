# compute_frame(): stacks header, legend, panels and caption using the spacing scale.

place_panel_rows <- function(state, spec, layout, spacing, height) {
  base <- spec$base_size
  gap <- spacing$panel_columns * base
  offsets <- column_offsets(spec, spacing)
  width <- (layout$right - layout$plot_left - gap * (spec$panel_columns - 1) - sum(offsets)) / spec$panel_columns
  for (row in seq_len(spec$panel_rows)) {
    if (row > 1) state$y <- state$y + spacing$panel_rows * base
    placed <- stack_lines(state, spec$sizes$panel, header_line_count(spec, row))
    state <- placed$state
    layout$panel_header_baselines[[row]] <- placed$baselines
    if (length(placed$baselines)) state$y <- state$y + spacing$panel_header * base
    if (row == 1 && isTRUE(spec$y_title)) {
      layout$y_title_left <- layout$left
      placed <- stack_lines(state, spec$sizes$label, 1)
      state <- placed$state
      layout$y_title_baseline <- placed$baselines
      state$y <- state$y + spacing$y_title * base
    }
    for (column in seq_len(spec$panel_columns)) {
      x <- layout$plot_left + (column - 1) * (width + gap) + sum(offsets[seq_len(column)])
      layout$panels[[length(layout$panels) + 1]] <- c(x, state$y, width, height)
    }
    state$y <- state$y + height + inner_tick_band(spec, row, spacing)
    titled <- has_row_titles(spec, row) && row < spec$panel_rows
    if (titled) {
      state$y <- state$y + spacing$x_title * base
      placed <- stack_lines(state, spec$sizes$label, 1)
      state <- placed$state
    }
    layout$x_title_row_baselines[row] <- list(if (titled) placed$baselines else NULL)
  }
  list(state = state, layout = layout)
}

place_bottom_block <- function(state, spec, layout, spacing) {
  base <- spec$base_size
  if (isTRUE(spec$x_tick_labels)) state$y <- state$y + spacing$x_tick_labels * spec$sizes$label
  if (bottom_title(spec)) {
    state$y <- state$y + spacing$x_title * base
    placed <- stack_lines(state, spec$sizes$label, 1)
    state <- placed$state
    layout$x_title_baseline <- placed$baselines
    if (has_row_titles(spec, spec$panel_rows)) layout$x_title_row_baselines[spec$panel_rows] <- list(placed$baselines)
  }
  if (spec$table_lines > 0) {
    state$y <- state$y + spacing$table_gap * base
    placed <- stack_lines(state, spec$sizes$label, spec$table_lines)
    state <- placed$state
    layout$table_baselines <- placed$baselines
  }
  if (spec$caption_lines > 0) {
    state$y <- state$y + spacing$content_caption * base
    placed <- stack_lines(state, spec$sizes$caption, spec$caption_lines)
    layout$caption_baselines <- placed$baselines
  }
  layout
}

compute_frame <- function(spec, metrics) {
  spec <- utils::modifyList(frame_defaults, spec)
  tokens <- hl_tokens()
  spacing <- tokens$spacing
  left <- spacing$margin * spec$base_size
  layout <- list(left = left, right = spec$width_pt - left,
                 plot_left = left + if (isTRUE(spec$y_labels)) spec$y_label_width_pt + spacing$y_labels_plot *
                   spec$base_size else 0,
                 title_baselines = numeric(), subtitle_baselines = numeric(), legend_row_centers = numeric(),
                 panel_header_baselines = list(), panels = list(), y_title_left = NULL, y_title_baseline = NULL,
                 x_title_baseline = NULL, x_title_row_baselines = list(), caption_baselines = numeric(),
                 table_baselines = numeric())
  state <- list(y = 0, metrics = metrics, line_gap = tokens$type$line_gap)
  placed <- place_header_block(state, spec, layout, spacing)
  height <- frame_panel_height(spec, placed$state$y, spacing, metrics, tokens$type$line_gap)
  placed <- place_panel_rows(placed$state, spec, placed$layout, spacing, height)
  place_bottom_block(placed$state, spec, placed$layout, spacing)
}
