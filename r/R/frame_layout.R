# compute_frame(): stacks header, legend, panels and caption using the spacing scale.

# Long y labels (or many columns) must leave room for the data; otherwise the panel would vanish or turn over.
check_panel_width <- function(spec, width, spacing) {
  if (width >= spacing$min_panel_width * spec$base_size) return(invisible())
  labels <- if (isTRUE(spec$y_labels)) sprintf("; the y labels take %.0f pt", spec$y_label_width_pt) else ""
  sides <- max(c(0, spec$side_widths))
  if (sides > 0) labels <- paste0(labels, sprintf("; the numbers beside the plot take %.0f pt", sides))
  stop(sprintf(paste0("hairline: figure too narrow: %.0f pt wide leaves %.1f pt per panel for %d panel columns%s; ",
                      "shorten the labels, use fewer columns, or use a wider size"), spec$width_pt, width,
               as.integer(spec$panel_columns), labels), call. = FALSE)
}

place_panel_rows <- function(state, spec, layout, spacing, heights) {
  base <- spec$base_size
  gap <- spacing$panel_columns * base
  offsets <- column_offsets(spec, spacing)
  # Room right of each column's panels for its numbers column (an n per bar), when it has one.
  sides <- c(unlist(spec$side_widths), rep(0, spec$panel_columns))[seq_len(spec$panel_columns)]
  width <- (layout$right - layout$plot_left - gap * (spec$panel_columns - 1) - sum(offsets) - sum(sides)) /
    spec$panel_columns
  check_panel_width(spec, width, spacing)
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
      x <- layout$plot_left + (column - 1) * (width + gap) + sum(offsets[seq_len(column)]) +
        sum(sides[seq_len(column - 1)])
      layout$panels[[length(layout$panels) + 1]] <- c(x, state$y, width, heights[row])
    }
    state$y <- state$y + heights[row] + inner_tick_band(spec, row, spacing)
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
  if (isTRUE(spec$x_tick_labels)) {
    state$y <- state$y + spacing$x_tick_labels * spec$sizes$label + (spec$x_tick_extra_pt %||% 0)
  }
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
  heights <- frame_panel_heights(spec, placed$state$y, spacing, metrics, tokens$type$line_gap)
  placed <- place_panel_rows(placed$state, spec, placed$layout, spacing, heights)
  place_bottom_block(placed$state, spec, placed$layout, spacing)
}
