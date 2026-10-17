# A small table under the x-axis (number at risk), its values aligned to x positions of the first panel;
# the same layout as the Python package's layout/table.py. Charts store it in plot@meta$hairline_table as
# list(heading = , rows = list(list(label = , colour = , x = <numeric>, text = <character>), ...)).

table_line_count <- function(table) if (is.null(table)) 0 else length(table$rows) + if (is.null(table$heading)) 0 else 1

table_label_offset <- function(settings) {
  spacing <- hl_tokens()$spacing
  (spacing$legend_swatch_square + spacing$legend_swatch_text) * settings$base_size
}

table_label_width <- function(parts) {
  if (is.null(parts$table)) return(0)
  style <- role_style(parts$settings, "label")
  rows <- parts$table$rows
  widest <- max(vapply(rows, function(row) text_width_pt(row$label, style), numeric(1)))
  values <- max(c(0, unlist(lapply(rows, function(row) vapply(row$text, text_width_pt, numeric(1), style = style)))))
  table_label_offset(parts$settings) + widest + values / 2
}

table_value_xs <- function(parts, plan) {
  if (is.null(parts$table)) return(numeric())
  box <- fitted_box(plan$layout$panels[[1]], parts$aspect)
  range <- parts$x_ranges[[1]]
  unlist(lapply(parts$table$rows, function(row) box[1] + (as.numeric(row$x) - range[1]) / diff(range) * box[3]))
}

table_grobs <- function(parts, plan) {
  table <- parts$table
  if (is.null(table)) return(list())
  settings <- parts$settings
  height <- plan$size[2]
  left <- plan$layout$left
  baselines <- plan$layout$table_baselines
  label <- role_style(settings, "label")
  ink <- role_style(settings, "label", colour = settings$neutral$ink)
  grobs <- list()
  if (!is.null(table$heading)) {
    grobs[[1]] <- text_grob_pt(table$heading, left, baselines[1], label, height)
    baselines <- baselines[-1]
  }
  side <- hl_tokens()$spacing$legend_swatch_square * settings$base_size
  cap <- font_metrics()$cap_height * label$size
  xs <- split(table_value_xs(parts, plan), rep(seq_along(table$rows), vapply(table$rows, function(row) {
    length(row$x)
  }, integer(1))))
  for (index in seq_along(table$rows)) {
    row <- table$rows[[index]]
    top <- baselines[index] - cap / 2 - side / 2
    grobs <- c(grobs, list(grid::rectGrob(grid::unit(left, "pt"), grid::unit(height - top - side, "pt"),
                                          grid::unit(side, "pt"), grid::unit(side, "pt"), just = c(0, 0),
                                          gp = grid::gpar(fill = row$colour, col = NA)),
                           text_grob_pt(row$label, left + table_label_offset(settings), baselines[index], label,
                                        height)),
               lapply(seq_along(row$text), function(item) {
                 text_grob_pt(row$text[item], xs[[index]][item], baselines[index], ink, height, "center")
               }))
  }
  grobs
}
