# Charts drawn in pt (donut, partition bars, Sankey): shared shape lists rendered by the frame.
# A chart stores a function in plot@meta$hairline_drawing that receives the plot box, a text-measuring
# function and the style, and returns shapes: polygons, lines and texts in pt from the top-left corner.

drawing_style <- function(settings) {
  tokens <- hl_tokens()
  base <- settings$base_size
  list(base = base, sizes = lapply(stats::setNames(nm = names(tokens$type$roles)), role_size, settings = settings),
       line_gap = tokens$type$line_gap, cap_height = font_metrics()$cap_height, neutral = settings$neutral,
       swatch = tokens$spacing$legend_swatch_square, swatch_text = tokens$spacing$legend_swatch_text,
       leader_width = tokens$reference$width * base, data_width = tokens$lines$data * base,
       axis_width = tokens$lines$axis * base, grid = tokens$lines$grid * base, descender = font_metrics()$descender)
}

measure_for <- function(settings) {
  function(text, role, weight = NULL) text_width_pt(text, role_style(settings, role, weight))
}

shape_grob <- function(shape, height, settings) {
  if (shape$kind == "polygon") {
    points <- shape_points(shape)
    return(grid::polygonGrob(grid::unit(points[, 1], "pt"), grid::unit(height - points[, 2], "pt"),
                             gp = grid::gpar(fill = shape$fill, col = NA, alpha = shape$alpha %||% 1)))
  }
  if (shape$kind == "line") {
    points <- shape_points(shape)
    return(grid::linesGrob(grid::unit(points[, 1], "pt"), grid::unit(height - points[, 2], "pt"),
                           gp = grid::gpar(col = shape$color, lwd = shape$width / 0.75, lineend = "butt",
                                           linejoin = "mitre", lty = shape_dash(shape))))
  }
  style <- role_style(settings, shape$role, shape$weight, shape$color)
  text_grob_pt(shape$text, shape$x, shape$y, style, height, shape$align)
}

shape_dash <- function(shape) {
  if (is.null(shape$dash)) "solid" else paste(sprintf("%X", as.integer(unlist(shape$dash))), collapse = "")
}

shape_points <- function(shape) {
  if (is.matrix(shape$points)) shape$points else do.call(rbind, lapply(shape$points, as.numeric))
}

drawing_shapes <- function(parts, layout) {
  if (is.null(parts$drawing)) return(list())
  box <- fitted_box(layout$panels[[1]], parts$aspect)
  parts$drawing(box, measure_for(parts$settings), drawing_style(parts$settings))
}

drawing_grobs <- function(shapes, height, settings) lapply(shapes, shape_grob, height = height, settings = settings)

drawing_texts <- function(shapes) {
  lapply(Filter(function(shape) shape$kind == "text", shapes), function(shape) c(shape$x, shape$y))
}
