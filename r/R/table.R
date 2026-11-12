# A small table under the x-axis (number at risk), its values aligned to x positions of the first panel;
# the same layout as the Python package's layout/table.py. Charts store it in plot@meta$hairline_table as
# list(heading = , rows = list(list(label = , colour = , x = <numeric>, text = <character>), ...)).

table_line_count <- function(table) if (is.null(table)) 0 else length(table$rows) + if (is.null(table$heading)) 0 else 1

# Each row's key takes the legend swatch of the series with the same label (a square if there is none).
table_keys <- function(parts) {
  if (is.null(parts$table)) return(character())
  kinds <- stats::setNames(vapply(parts$legend, `[[`, character(1), "kind"),
                           vapply(parts$legend, `[[`, character(1), "label"))
  vapply(parts$table$rows, function(row) if (row$label %in% names(kinds)) kinds[[row$label]] else "square",
         character(1))
}

table_label_offset <- function(parts) {
  spacing <- hl_tokens()$spacing
  base <- parts$settings$base_size
  widths <- vapply(table_keys(parts), swatch_width, numeric(1), base = base, spacing = spacing)
  max(c(widths, if (!length(widths)) spacing$legend_swatch_square * base)) + spacing$legend_swatch_text * base
}

table_label_width <- function(parts) {
  if (is.null(parts$table)) return(0)
  style <- role_style(parts$settings, "label")
  rows <- parts$table$rows
  # A compact row's label ("n") takes the room its full row leaves, so existing figures keep their frame.
  widest <- max(vapply(rows, function(row) text_width_pt(row$label, style), numeric(1)))
  values <- max(c(0, unlist(lapply(rows, function(row) vapply(row$text, text_width_pt, numeric(1), style = style)))))
  table_label_offset(parts) + widest + values / 2
}

table_value_xs <- function(parts, plan) {
  if (is.null(parts$table)) return(numeric())
  box <- fitted_box(plan$layout$panels[[1]], parts$aspect)
  range <- parts$x_ranges[[1]]
  unlist(lapply(parts$table$rows, function(row) box[1] + (as.numeric(row$x) - range[1]) / diff(range) * box[3]))
}

# Where neighbouring texts of a row come closer than the gap of x-axis labels (`ticks.label_rows_gap`): the figure's
# message saying what would fit; NULL when they stand apart. As Python's table_collision().
table_collision <- function(row, xs, range, style) {
  gap <- hl_tokens()$ticks$label_rows_gap * style$size
  widths <- vapply(row$text, text_width_pt, numeric(1), style = style)
  starts <- xs - widths * edge_hjust((as.numeric(row$x) - range[1]) / diff(range))
  ordered <- order(xs)
  for (index in seq_len(length(ordered) - 1)) {
    first <- ordered[index]
    second <- ordered[index + 1]
    room <- starts[second] - (starts[first] + widths[first])
    if (room < gap) {
      return(sprintf(paste("hairline: the numbers under the x axis do not fit side by side: '%s' and '%s' leave %.1f",
                           "pt between them, and need %.1f pt. Show fewer stats or groups, use a wider size, or a",
                           "chart that lists the numbers in a column, such as hl_spread()"),
                     row$text[first], row$text[second], room, gap))
    }
  }
  NULL
}

# Each row as drawn: in full, or in its compact form (list(label, text) at the same x) when the full texts would
# meet; a row that fits in neither stops the figure. As Python's fitted_rows().
fitted_table_rows <- function(rows, xs, range, style) {
  lapply(seq_along(rows), function(index) {
    row <- rows[[index]]
    problem <- table_collision(row, xs[[index]], range, style)
    if (!is.null(problem) && !is.null(row$compact)) {
      row$label <- row$compact$label
      row$text <- row$compact$text
      problem <- table_collision(row, xs[[index]], range, style)
    }
    if (!is.null(problem)) stop(layout_error(problem))
    row
  })
}

# The table's rows fit, in full or compact, before anything is drawn (a device left mid-drawing stays locked).
check_table <- function(parts, plan) {
  table <- parts$table
  if (is.null(table)) return(invisible())
  ink <- role_style(parts$settings, "label", colour = parts$settings$neutral$ink)
  xs <- split(table_value_xs(parts, plan), rep(seq_along(table$rows), lengths(lapply(table$rows, `[[`, "x"))))
  fitted_table_rows(table$rows, xs, parts$x_ranges[[1]], ink)
  invisible()
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
  range <- parts$x_ranges[[1]]
  grobs <- list()
  if (!is.null(table$heading)) {
    grobs[[1]] <- text_grob_pt(table$heading, left, baselines[1], label, height)
    baselines <- baselines[-1]
  }
  cap <- font_metrics()$cap_height * label$size
  keys <- table_keys(parts)
  lines <- scaled_lines(line_scale(fitted_box(plan$layout$panels[[1]], parts$aspect)[3]))
  xs <- split(table_value_xs(parts, plan), rep(seq_along(table$rows), vapply(table$rows, function(row) {
    length(row$x)
  }, integer(1))))
  rows <- fitted_table_rows(table$rows, xs, range, ink)
  for (index in seq_along(rows)) {
    row <- rows[[index]]
    if (!is.null(row$colour)) {
      key <- list(x = left, kind = keys[index], colour = row$colour)
      grobs[[length(grobs) + 1]] <- swatch_grob(key, baselines[index] - cap / 2, height, settings$base_size,
                                                hl_tokens()$spacing, lines)
    }
    grobs <- c(grobs, list(text_grob_pt(row$label, left + table_label_offset(parts), baselines[index], label,
                                        height)),
               lapply(seq_along(row$text), function(item) {
                 align <- c("left", "right", "center")[match(edge_hjust((row$x[item] - range[1]) / diff(range)),
                                                             c(0, 1, 0.5))]
                 text_grob_pt(row$text[item], xs[[index]][item], baselines[index], ink, height, align)
               }))
  }
  grobs
}
