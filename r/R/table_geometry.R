# Table geometry in pt: a header row over hairline rules, body rows on a fixed pitch, text columns left-aligned and
# numbers right-aligned, the first column wrapped when the table is wider than the figure. Pure: the same spec gives
# the same shapes as the Python package's charts/table_geometry.py.

table_indent <- "  "

# Leading pairs of spaces as indent levels ("  Female" under "Sex, n (%)"), and the text without them.
indent_of <- function(content) {
  stripped <- sub("^ +", "", content)
  list(level = (nchar(content) - nchar(stripped)) %/% nchar(table_indent), text = stripped)
}

cell_width <- function(content, measure, weight, step) {
  indent <- indent_of(content)
  indent$level * step + measure(indent$text, "label", weight)
}

widest_cell <- function(cells, measure, weight, step) {
  max(c(0, vapply(cells, cell_width, numeric(1), measure = measure, weight = weight, step = step)))
}

widest_word <- function(content, measure, weight) {
  words <- strsplit(trimws(content), "\\s+")[[1]]
  max(c(0, vapply(words[nzchar(words)], measure, numeric(1), role = "label", weight = weight)))
}

# Each column as wide as its widest cell and heading. A table wider than the box first wraps its headings (down to
# their longest word; those that need least take back the room left first), then its first column, down to
# `table.min_column` x the base size; beyond that it is an error.
fitted_widths <- function(spec, box, measure, style) {
  rules <- hl_tokens()$table
  base <- style$base
  heading_weight <- rules$header_weight
  gap <- rules$column_gap * base
  columns <- seq_along(spec$header)
  body <- vapply(columns, function(index) {
    widest_cell(vapply(spec$rows, `[[`, character(1), index), measure, NULL, base)
  }, numeric(1))
  headings <- vapply(spec$header, cell_width, numeric(1), measure = measure, weight = heading_weight, step = base,
                     USE.NAMES = FALSE)
  natural <- pmax(body, headings)
  room <- box[3] - gap * (length(natural) - 1)
  if (sum(natural) <= room + wrap_tolerance) return(natural)
  widths <- pmax(body, vapply(spec$header, widest_word, numeric(1), measure = measure, weight = heading_weight,
                              USE.NAMES = FALSE))
  spare <- room - sum(widths)
  # The headings that need least take back their room first, so as few as possible wrap.
  for (index in columns[order(natural - widths, columns)]) {
    if (spare <= 0) break
    grow <- min(spare, natural[index] - widths[index])
    widths[index] <- widths[index] + grow
    spare <- spare - grow
  }
  if (spare >= -wrap_tolerance) return(widths)
  first <- widths[1] + spare
  if (first < rules$min_column * base) {
    stop(sprintf(paste("hairline: table: the columns need %.0f pt even with wrapped headings, but the figure leaves",
                       "%.0f pt and the first column cannot wrap narrower than %.0f pt. Use a wider size, fewer",
                       "columns or shorter headings"), sum(widths) + gap * (length(widths) - 1), box[3],
                 rules$min_column * base), call. = FALSE)
  }
  c(first, widths[-1])
}

cell_lines <- function(content, width, measure, weight, step) {
  indent <- indent_of(content)
  if (cell_width(content, measure, weight, step) <= width + wrap_tolerance) {
    return(list(level = indent$level, lines = indent$text))
  }
  list(level = indent$level,
       lines = wrap_words(indent$text, width - indent$level * step + wrap_tolerance, measure, "label", weight))
}

table_anchor <- function(align, left, width) {
  switch(align, left = left, right = left + width, center = left + width / 2)
}

# One row's texts, each cell's lines from its top (with `bottom`, a heading row, on its last line); returns the shapes
# and the row's height.
table_row_shapes <- function(cells, top, lefts, widths, spec, measure, style, weight, bottom = FALSE) {
  lead <- line_height(style, "label")
  pitch <- hl_tokens()$table$row_pitch * lead
  wrapped <- lapply(seq_along(cells), function(index) {
    cell_lines(cells[[index]], widths[index], measure, weight, style$base)
  })
  tallest <- max(vapply(wrapped, function(cell) length(cell$lines), integer(1)))
  shapes <- list()
  for (index in seq_along(cells)) {
    align <- spec$align[index]
    cell <- wrapped[[index]]
    shift <- if (bottom) (tallest - length(cell$lines)) * lead else 0
    for (number in seq_along(cell$lines)) {
      baseline <- baseline_for(top + pitch / 2 + (number - 1) * lead + shift, style, "label")
      x <- table_anchor(align, lefts[index] + if (align == "left") cell$level * style$base else 0, widths[index])
      shapes[[length(shapes) + 1]] <- c(shape_text(x, baseline, cell$lines[number], "label", style$neutral$ink, align,
                                                   weight), part = "cell")
    }
  }
  list(shapes = shapes, height = pitch + (tallest - 1) * lead)
}

table_rule <- function(left, right, y, style) {
  list(kind = "line", points = rbind(c(left, y), c(right, y)), color = style$neutral$axis, width = style$axis_width,
       role = "rule")
}

# Rules above the header, under it and under the last row (the three rules of a journal table); bold rows in the key
# weight.
table_drawing <- function(spec, box, measure, style) {
  rules <- hl_tokens()$table
  widths <- fitted_widths(spec, box, measure, style)
  gap <- rules$column_gap * style$base
  lefts <- box[1] + c(0, cumsum(widths + gap))[seq_along(widths)]
  right <- lefts[length(lefts)] + widths[length(widths)]
  y <- box[2]
  shapes <- list(table_rule(box[1], right, y, style))
  header <- table_row_shapes(spec$header, y, lefts, widths, spec, measure, style, rules$header_weight, TRUE)
  shapes <- c(shapes, header$shapes)
  y <- y + header$height
  shapes[[length(shapes) + 1]] <- table_rule(box[1], right, y, style)
  for (index in seq_along(spec$rows)) {
    weight <- if (index %in% spec$bold) rules$header_weight else NULL
    row <- table_row_shapes(spec$rows[[index]], y, lefts, widths, spec, measure, style, weight)
    shapes <- c(shapes, row$shapes)
    y <- y + row$height
  }
  c(shapes, list(table_rule(box[1], right, y, style)))
}
