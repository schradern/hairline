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
                             gp = grid::gpar(fill = shape$fill, col = shape$edge %||% NA, alpha = shape$alpha %||% 1,
                                             lwd = (shape$edge_width %||% 0) / 0.75, linejoin = "mitre")))
  }
  if (shape$kind == "line") {
    points <- shape_points(shape)
    return(grid::linesGrob(grid::unit(points[, 1], "pt"), grid::unit(height - points[, 2], "pt"),
                           gp = grid::gpar(col = shape$color, lwd = shape$width / 0.75, lineend = "butt",
                                           linejoin = "round", lty = shape_dash(shape), alpha = shape$alpha %||% 1)))
  }
  style <- role_style(settings, shape$role, shape$weight, shape$color)
  text_grob_pt(shape$text, shape$x, shape$y, style, height, shape$align, shape$rotation %||% 0)
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
  style <- drawing_style(parts$settings)
  style$data_width <- style$data_width * line_scale(box[3])
  parts$drawing(box, measure_for(parts$settings), style)
}

drawing_grobs <- function(shapes, height, settings) lapply(shapes, shape_grob, height = height, settings = settings)

drawing_texts <- function(shapes) {
  lapply(Filter(function(shape) shape$kind == "text", shapes), function(shape) c(shape$x, shape$y))
}

# Lowest point the shapes reach: outlines, texts down to their descenders, and a text turned upright (rotated 90
# degrees, anchored at its end) down to its start, its length below the anchor.
content_bottom <- function(shapes, style, measure = NULL) {
  max(vapply(shapes, function(shape) {
    if (shape$kind == "text") {
      if (is.null(shape$rotation)) return(shape$y + style$descender * style$sizes[[shape$role]])
      upright <- shape$rotation == 90 && identical(shape$align, "right") && !is.null(measure)
      return(shape$y + if (upright) measure(shape$text, shape$role, shape$weight) else 0)
    }
    max(shape_points(shape)[, 2])
  }, numeric(1)))
}

# Pixels the measuring device of fitted_size_mm() may hold: 72 dpi up to about A0, a lower resolution beyond.
fit_device_megapixels <- 16

# Charts drawn from shapes that set plot@meta$hairline_fit_height get a figure height that ends where their content
# ends (shorter, or taller when it overflows), as the Python package's fit_height() does. The device only hosts the
# layout pass (hairline measures text itself), so a very large figure gets a lower resolution, not a buffer that
# grows with the square of its width.
fitted_size_mm <- function(plot, size_mm) {
  if (!isTRUE(plot@meta$hairline_fit_height)) return(size_mm)
  path <- tempfile(fileext = ".png")
  res <- min(72, sqrt(fit_device_megapixels * 1e6 / prod(size_mm / 25.4)))
  ragg::agg_png(path, width = size_mm[1], height = size_mm[2], units = "mm", res = res)
  on.exit({
    grDevices::dev.off()
    unlink(path)
  })
  frame <- ggplot2::ggplotGrob(plot)
  if (!inherits(frame, "hairline_frame")) return(size_mm)
  plan <- plan_frame(frame$parts, size_mm / 25.4 * 72)
  box <- fitted_box(plan$layout$panels[[1]], frame$parts$aspect)
  slack <- box[2] + box[4] - content_bottom(plan$shapes, drawing_style(frame$parts$settings),
                                            measure_for(frame$parts$settings))
  c(size_mm[1], size_mm[2] - slack / 72 * 25.4)
}
