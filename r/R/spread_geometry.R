# Spread rows in pt, mirroring the Python spread_geometry.py: group names on the left, range line, interval bar,
# median dot, mean diamond and reference tick on a shared axis with grid lines, the key numbers right-aligned beside
# the plot (or, on a figure too narrow for both, on a line under each row), the axis title under the numbers.

# The mean's open diamond: its half-diagonal against a dot's radius.
diamond_size <- 1.3

# The mean: an open diamond in the row's colour, filled with the surface so the band shows round it.
open_diamond <- function(x, centre, colour, style) {
  half <- diamond_size * dot_size(style) / 2
  list(kind = "polygon", points = rbind(c(x - half, centre), c(x, centre - half), c(x + half, centre),
                                        c(x, centre + half)),
       fill = style$neutral$surface, edge = colour, edge_width = style$data_width * open_edge, role = "mean")
}

spread_letters <- letters

# A section's name over its rows, at the key weight, after its letter (a, b, c) when the sections are lettered.
heading_shapes <- function(name, index, lettered, x, baseline, measure, style) {
  weight <- hl_tokens()$type$key_weight
  ink <- style$neutral$ink
  shapes <- list()
  if (lettered) {
    letter <- spread_letters[(index %% length(spread_letters)) + 1]
    shapes[[1]] <- c(shape_text(x, baseline, letter, "label", ink, "left", weight), part = "letter")
    x <- x + measure(letter, "label", weight) + hl_tokens()$spacing$panel_letter_gap * style$base
  }
  c(shapes, list(c(shape_text(x, baseline, name, "label", ink, "left", weight), part = "heading")))
}

# The lines top to bottom: a heading where a section starts, then its rows.
section_lines <- function(rows) {
  lines <- list()
  current <- NULL
  for (row in rows) {
    if (!is.null(row$section) && !identical(row$section, current)) {
      lines[[length(lines) + 1]] <- list(kind = "heading", entry = row$section)
    }
    current <- row$section
    lines[[length(lines) + 1]] <- list(kind = "row", entry = row)
  }
  lines
}

# The interval bar: the IQR as the light band, an SD or CI as a slim solid bar (`summary.thin_bar` of it).
spread_bar_shape <- function(row, centre, half, scale, rules) {
  if (row$bar$slim) half <- half * hl_tokens()$summary$thin_bar
  points <- rbind(c(scale(row$bar$low), centre - half), c(scale(row$bar$high), centre - half),
                  c(scale(row$bar$high), centre + half), c(scale(row$bar$low), centre + half))
  list(kind = "polygon", points = points, fill = row$color, alpha = if (row$bar$slim) 1 else rules$band_opacity,
       role = "band")
}

# Where a row's tooltip points: its median, else its mean, else the middle of its bar or range.
spread_row_centre <- function(row) {
  if (row$show_median) return(row$median)
  if (!is.null(row$mean)) return(row$mean)
  if (!is.null(row$bar)) (row$bar$low + row$bar$high) / 2 else (row$low + row$high) / 2
}

# The marks of `summary` (range line, interval bar, median dot, mean diamond) and the group's mark; the first of them
# carries the row's tooltip.
spread_row_shapes <- function(row, centre, pitch, scale, style, rules) {
  half <- rules$band * pitch / 2
  shapes <- list()
  if (row$range) {
    shapes[[length(shapes) + 1]] <- list(kind = "line", points = rbind(c(scale(row$low), centre),
                                                                       c(scale(row$high), centre)),
                                         color = style$neutral$faint, width = style$leader_width, role = "range")
  }
  if (!is.null(row$bar)) shapes[[length(shapes) + 1]] <- spread_bar_shape(row, centre, half, scale, rules)
  if (row$show_median) {
    shapes[[length(shapes) + 1]] <- forest_marker(scale(row$median), centre, dot_size(style), "dot", row$color)
  }
  if (!is.null(row$mean)) shapes[[length(shapes) + 1]] <- open_diamond(scale(row$mean), centre, row$color, style)
  if (!is.null(row$mark)) {
    tick <- rules$mark * half
    x <- scale(row$mark)
    shapes[[length(shapes) + 1]] <- list(kind = "line", points = rbind(c(x, centre - tick), c(x, centre + tick)),
                                         color = style$neutral$ink, width = style$leader_width, role = "mark")
  }
  if (length(shapes)) {
    shapes[[1]]$tip <- paste0(row$name, ": ", paste(vapply(row$pairs, paste, character(1), collapse = " "),
                                                    collapse = ", "))
    shapes[[1]]$tip_at <- c(scale(spread_row_centre(row)), centre - half)
  }
  lapply(shapes, function(shape) c(shape, series = row$name))
}

spread_pair_width <- function(pair, measure) {
  measure(paste0(pair[1], " "), "label") + measure(pair[2], "label", hl_tokens()$type$value_weight)
}

# Width of each key-number column: one column per statistic, so labels line up from row to row.
spread_stat_widths <- function(spec, measure) {
  count <- max(vapply(spec$rows, function(row) length(row$pairs), integer(1)))
  vapply(seq_len(count), function(index) {
    max(c(0, unlist(lapply(spec$rows, function(row) {
      if (index <= length(row$pairs)) spread_pair_width(row$pairs[[index]], measure)
    }))))
  }, numeric(1))
}

# Left edges of the key-number columns from `start`, separated like a panel header's key numbers.
spread_stat_columns <- function(widths, start, gap) {
  start + c(0, cumsum(widths + gap))[seq_along(widths)]
}

# Under the rows, a line of key numbers and a row of name and plot must each fit the width.
spread_check_room <- function(width, block, least, names, gap) {
  need <- max(block, names + gap + least)
  if (width >= need) return(invisible())
  stop(sprintf(paste("hairline: spread: the figure leaves %.0f pt for the rows, which need at least %.0f pt: the key",
                     "numbers take %.0f pt in one line, the group names %.0f pt beside a plot of %.0f pt. Shorten",
                     "the group names, show fewer stats, or use a wider size"), width, need, block, names, least),
       call. = FALSE)
}

# The plot span and the key-number columns. The numbers sit right-aligned beside the plot while it keeps at least
# `min_plot`; on a narrower figure they move to a line under each row, from the row's left edge, and the plot spans
# the width the names leave. No statistic is dropped.
spread_layout <- function(spec, box, measure, style, rules) {
  pair_gap <- hl_tokens()$spacing$stats_pair * style$base
  gap <- rules$column_gap * style$base
  least <- rules$min_plot * style$base
  widths <- spread_stat_widths(spec, measure)
  block <- if (length(widths)) sum(widths) + pair_gap * (length(widths) - 1) else 0
  names <- max(vapply(spec$rows, function(row) measure(row$name, "label"), numeric(1)))
  left <- box[1] + names + gap
  right <- box[1] + box[3]
  if (!length(widths)) return(list(plot = c(left, right), lefts = numeric(), under = FALSE))
  if (numbers_beside(spec$numbers, right - block - gap - left, least, style$base, "spread")) {
    return(list(plot = c(left, right - block - gap), lefts = spread_stat_columns(widths, right - block, pair_gap),
                under = FALSE))
  }
  spread_check_room(box[3], block, least, names, gap)
  list(plot = c(left, right), lefts = spread_stat_columns(widths, box[1], pair_gap), under = TRUE)
}

# Label in faint, value in muted at the value weight: the panel header's key-number style.
spread_pair_texts <- function(pairs, lefts, baseline, measure, style) {
  weight <- hl_tokens()$type$value_weight
  unlist(lapply(seq_along(pairs), function(index) {
    label <- paste0(pairs[[index]][1], " ")
    list(shape_text(lefts[index], baseline, label, "label", style$neutral$faint),
         shape_text(lefts[index] + measure(label, "label"), baseline, pairs[[index]][2], "label",
                    style$neutral$muted, "left", weight))
  }), recursive = FALSE)
}

spread_title_shape <- function(spec, right, axis_y, style, rules) {
  if (is.null(spec$axis_title)) return(list())
  size <- style$sizes$label
  ticks <- axis_y + rules$axis_gap * style$base + style$cap_height * size
  baseline <- ticks + style$descender * size + hl_tokens()$spacing$x_title * style$base + style$cap_height * size
  list(c(shape_text(right, baseline, spec$axis_title, "label", style$neutral$muted, "right"), part = "title"))
}

# Rows keep their pitch (the figure's height follows them); a row whose numbers sit under it is a line taller.
spread_drawing <- function(spec, box, measure, style) {
  rules <- hl_tokens()$spread
  layout <- spread_layout(spec, box, measure, style, rules)
  left <- layout$plot[1]
  right <- layout$plot[2]
  lead <- line_height(style, "label")
  scale <- forest_scale(spec$axis, FALSE, left, right)
  line <- rules$row_pitch * lead
  pitch <- line + if (layout$under) lead else 0
  lines <- section_lines(spec$rows)
  heights <- vapply(lines, function(entry) if (entry$kind == "heading") line else pitch, numeric(1))
  above <- drawn_reference_height(spec, style)
  bottom <- box[2] + above + sum(heights)
  shapes <- lapply(spec$axis$breaks, function(value) {
    list(kind = "line", points = rbind(c(scale(value), box[2] + above), c(scale(value), bottom)),
         color = style$neutral$grid, width = style$grid, role = "grid")
  })
  shapes <- c(shapes, drawn_reference_shapes(spec, scale, box[2], bottom, style))
  top <- box[2] + above
  headings <- 0
  for (index in seq_along(lines)) {
    entry <- lines[[index]]$entry
    centre <- top + line / 2
    baseline <- baseline_for(centre, style, "label")
    top <- top + heights[index]
    if (lines[[index]]$kind == "heading") {
      shapes <- c(shapes, heading_shapes(entry, headings, isTRUE(spec$letters), box[1], baseline, measure, style))
      headings <- headings + 1
      next
    }
    shapes <- c(shapes, spread_row_shapes(entry, centre, line, scale, style, rules),
                list(shape_text(box[1], baseline, entry$name, "label", style$neutral$ink)),
                spread_pair_texts(entry$pairs, layout$lefts, baseline + if (layout$under) lead else 0, measure, style))
  }
  axis <- list(axis = spec$axis, favours = NULL, null = NULL)
  c(shapes, forest_axis_shapes(axis, scale, c(left, right), bottom, style, rules),
    spread_title_shape(spec, right, bottom, style, rules))
}

# spread_spec() with a block of rows per value of `facet`: every row keyed by facet and group, the blocks drawn as
# sections, each group in its own colour in every block (as `colors`), names shown without the facet. As Python's
# faceted_spec().
