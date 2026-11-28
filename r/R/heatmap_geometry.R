# Heatmap geometry in pt, mirroring the Python charts/heatmap_geometry.py: one cell per grid point, its edges halfway
# to the neighbouring values, its axis text where the frame puts an axis chart's (the spacing tokens). Beside a
# surface it shares the surface's height and leaves its cells untagged, since the surface's script links the two.

# The flat spec with every text's width in pt and the colours and sizes the drawing needs. As Python's
# heatmap_scene().
heatmap_scene <- function(spec, measure, style) {
  size <- style$sizes$label
  ticks <- lapply(stats::setNames(nm = c("x", "y")), function(axis) {
    lapply(spec$ticks[[axis]], function(tick) c(tick, list(width = measure(tick$text, "label"))))
  })
  rules <- hl_tokens()
  spacing <- rules$spacing
  base <- style$base
  list(x_edges = unlist(spec$x_edges), y_edges = unlist(spec$y_edges), fills = spec$fills, tips = spec$tips,
       titles = spec$titles[c("x", "y")], ticks = ticks,
       text = list(cap = style$cap_height * size, descender = style$descender * size,
                   ascender = style$ascender * size, ticks = style$neutral$faint, titles = style$neutral$muted),
       gaps = list(y_labels = spacing$y_labels_plot * base, x_pad = spacing$x_tick_pad * size,
                   x_band = spacing$x_tick_labels * size, x_title = spacing$x_title * base,
                   y_title = spacing$y_title * base),
       seam = rules$surface$seam_pt, aspect = rules$heatmap$aspect,
       margins = heatmap_margin_scene(spec$margins, measure, style))
}

# The cells' rectangle c(x, y, width, height). As Python's plot_frame().
heatmap_plot_frame <- function(scene, box, height = NULL) {
  glyphs <- scene$text
  gaps <- scene$gaps
  line <- glyphs$cap + glyphs$descender
  reserve <- heatmap_margin_reserve(scene$margins, line)
  widths <- vapply(scene$ticks$y, `[[`, 0, "width")
  left <- box[1] + (if (length(widths)) max(widths) else 0) + gaps$y_labels
  top <- box[2] + (if (nzchar(scene$titles$y)) line + gaps$y_title else glyphs$cap / 2)
  below <- gaps$x_band + (if (nzchar(scene$titles$x)) gaps$x_title + line else 0)
  last <- if (length(scene$ticks$x)) scene$ticks$x[[length(scene$ticks$x)]]$width / 2 else 0
  width <- box[1] + box[3] - max(last, reserve[2]) - left
  room <- (height %||% box[4]) - (top - box[2]) - below
  tall <- if (is.null(height)) min(room, width * scene$aspect) else room
  # The bars add to the figure's height rather than take it from the cells, which keep the aspect whatever the box.
  if (!is.null(scene$margins) && is.null(height)) tall <- width * scene$aspect
  top <- top + reserve[1]
  if (width <= 0 || tall <= 0) {
    stop(sprintf(paste("hairline: heatmap: the axis labels leave no room for the cells in %.0f x %.0f pt.",
                       "Shorten the labels or use a wider size"), box[3], box[4]), call. = FALSE)
  }
  c(left, top, width, tall)
}

# The tooltip of grid point (column, row): its row as the series, then its x, y and value. As Python's cell_shapes().
heatmap_tag <- function(shape, scene, column, row) {
  titles <- scene$titles
  where <- paste(Filter(nzchar, c(titles$y, scene$tips$y[[row]])), collapse = " ")
  what <- paste(Filter(nzchar, c(titles$x, scene$tips$x[[column]])), collapse = " ")
  tagged_shape(shape, where, paste0(what, ", ", where, ": ", scene$tips$z[[row]][[column]]))
}

# A rectangle per grid point with a value, and its c(x, y, width, height, column, row) for the script (0-based
# column and row, as the script reads them). As Python's cell_shapes().
heatmap_cell_shapes <- function(scene, plot, tag) {
  xs <- scene$x_edges
  ys <- scene$y_edges
  shapes <- cells <- list()
  for (row in seq_len(length(ys) - 1)) {
    for (column in seq_len(length(xs) - 1)) {
      fill <- scene$fills[[row]][[column]]
      if (is.null(fill)) next
      left <- plot[1] + xs[column] * plot[3]
      right <- plot[1] + xs[column + 1] * plot[3]
      top <- plot[2] + (1 - ys[row + 1]) * plot[4]
      bottom <- plot[2] + (1 - ys[row]) * plot[4]
      shape <- list(kind = "polygon", points = rbind(c(left, top), c(right, top), c(right, bottom), c(left, bottom)),
                    fill = fill, edge = fill, edge_width = scene$seam, part = "cell")
      shapes[[length(shapes) + 1]] <- if (tag) heatmap_tag(shape, scene, column, row) else shape
      cells[[length(cells) + 1]] <- c(left, top, right - left, bottom - top, column - 1, row - 1)
    }
  }
  list(shapes = shapes, cells = cells)
}

# Cells, the marginal bars, then tick labels and titles; and the cells' rectangles for the script. As Python's
# heatmap_layout().
heatmap_layout <- function(scene, box, height = NULL, tag = TRUE) {
  plot <- heatmap_plot_frame(scene, box, height)
  drawn <- heatmap_cell_shapes(scene, plot, tag)
  drawn$shapes <- c(drawn$shapes, heatmap_margin_shapes(scene, plot))
  glyphs <- scene$text
  gaps <- scene$gaps
  texts <- lapply(scene$ticks$y, function(tick) {
    c(shape_text(plot[1] - gaps$y_labels, plot[2] + (1 - tick$at) * plot[4] + glyphs$cap / 2, tick$text, "label",
                 glyphs$ticks, "right"), part = "tick")
  })
  bottom <- plot[2] + plot[4]
  baseline <- bottom + gaps$x_pad + glyphs$ascender
  texts <- c(texts, lapply(scene$ticks$x, function(tick) {
    c(shape_text(plot[1] + tick$at * plot[3], baseline, tick$text, "label", glyphs$ticks, "center"), part = "tick")
  }))
  if (nzchar(scene$titles$y)) {
    texts <- c(texts, list(c(shape_text(box[1], box[2] + glyphs$cap, scene$titles$y, "label", glyphs$titles),
                             part = "title")))
  }
  if (nzchar(scene$titles$x)) {
    below <- bottom + gaps$x_band + gaps$x_title + glyphs$cap
    texts <- c(texts, list(c(shape_text(plot[1] + plot[3], below, scene$titles$x, "label", glyphs$titles, "right"),
                             part = "title")))
  }
  list(shapes = c(drawn$shapes, texts), cells = drawn$cells)
}

# The standalone heatmap, each cell a tooltip target of its row. As Python's heatmap_shapes().
heatmap_shapes <- function(scene, box) heatmap_layout(scene, box)$shapes
