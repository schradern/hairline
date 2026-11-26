# Surface, mirroring the Python charts/surface.py: one value over two numeric axes drawn as a turned 3D surface from a
# fixed viewpoint, its height binned into the steps of a ramp and keyed in the legend row. Turnable in the HTML export.

surface_chart <- "surface"

# At least one cell with all four corners. As Python's check_cells().
surface_check_cells <- function(grid, z) {
  known <- is.finite(grid)
  rows <- nrow(grid)
  columns <- ncol(grid)
  cells <- known[-rows, -columns, drop = FALSE] & known[-1, -columns, drop = FALSE] &
    known[-rows, -1, drop = FALSE] & known[-1, -1, drop = FALSE]
  if (!any(cells)) {
    stop(sprintf(paste("hairline: %s: no cell of the grid has '%s' at all four corners, so there is no surface to",
                       "draw; fill the gaps or use a coarser grid"), surface_chart, z), call. = FALSE)
  }
}

# Round values within the axis's range, placed on the cube's -1 to 1. As Python's cube_ticks().
surface_cube_ticks <- function(values) {
  low <- values[1]
  high <- values[length(values)]
  grid_inner_ticks(low, high, function(tick) 2 * (tick - low) / (high - low) - 1)
}

# The value axis's breaks, placed on the cube's height (centred on zero). As Python's height_ticks().
surface_height_ticks <- function(breaks, limits, height, percent) {
  texts <- grid_value_texts(breaks, percent)
  lapply(seq_along(breaks), function(k) {
    list(at = height * ((breaks[k] - limits[1]) / (limits[2] - limits[1]) - 0.5), text = texts[[k]])
  })
}

surface_checked_view <- function(elevation, azimuth) {
  rules <- hl_tokens()$surface
  limits <- unlist(rules$elevation_limits)
  elevation <- as.numeric(elevation %||% rules$elevation)
  if (elevation < limits[1] || elevation > limits[2]) {
    stop(sprintf("hairline: %s: elevation %g must lie between %g and %g degrees", surface_chart, elevation,
                 limits[1], limits[2]), call. = FALSE)
  }
  azimuth <- as.numeric(azimuth %||% rules$azimuth)
  list(elevation = elevation, azimuth = (azimuth + 180) %% 360 - 180)
}

# Everything the drawing needs, independent of the font. As Python's surface_spec().
surface_spec <- function(data, x, y, z, titles, colors = NULL, percent = FALSE, gradient = FALSE, heatmap = FALSE,
                         view = NULL) {
  found <- read_grid(data, x, y, z, surface_chart)
  xs <- found$xs
  ys <- found$ys
  grid <- found$grid
  surface_check_cells(grid, z)
  rules <- hl_tokens()$surface
  breaks <- nice_breaks(min(grid, na.rm = TRUE), max(grid, na.rm = TRUE), rules$ticks)
  scale <- grid_colour_scale(grid, breaks, colors, gradient)
  limits <- scale$key$limits
  height <- rules$height
  normal <- height * ((grid - limits[1]) / (limits[2] - limits[1]) - 0.5)
  spec <- list(xs = as.list(2 * (xs - xs[1]) / (xs[length(xs)] - xs[1]) - 1),
               ys = as.list(2 * (ys - ys[1]) / (ys[length(ys)] - ys[1]) - 1),
               zs = lapply(seq_len(nrow(normal)), function(row) {
                 lapply(normal[row, ], function(value) if (is.finite(value)) value else NULL)
               }),
               fills = grid_fills(grid_corner_means(grid), scale), height = height,
               view = view %||% surface_checked_view(NULL, NULL),
               ticks = list(x = surface_cube_ticks(xs), y = surface_cube_ticks(ys),
                            z = surface_height_ticks(breaks, limits, height, percent)),
               titles = titles, key = scale$key, tips = grid_tips(xs, ys, grid, percent))
  spec$description <- alt_described("kind_surface", alt_grid_extremes(grid, spec$tips, titles))
  if (heatmap) spec$flat <- heatmap_flat_spec(xs, ys, grid, scale, titles, percent)
  spec
}

# The panel's drawing: the surface, or the surface and its heatmap side by side. As Python's surface_drawing().
surface_drawing <- function(spec) {
  function(box, measure, style) {
    scene <- surface_scene(spec, measure, style)
    if (is.null(spec$flat)) return(surface_scene_shapes(scene, box))
    surface_pair_layout(scene, heatmap_scene(spec$flat, measure, style), box)$shapes
  }
}

#' 3D surface
#'
#' `z` over a grid of `x` and `y` (one row per pair; a pair without a row
#' leaves a gap) as a 3D surface seen from `elevation` degrees above the
#' floor, turned by `azimuth` degrees, its height binned into the steps of
#' the ramp `colors` (or blended along it with `gradient = TRUE`) and keyed
#' in the legend row. It shows the shape at
#' once; read exact values from a 2D chart beside it. The HTML export
#' (`hl_save(..., formats = "html")`) lets the reader turn it.
#'
#' @param data A data frame with one row per (`x`, `y`) pair.
#' @param x,y Numeric columns spanning the floor.
#' @param z The numeric column drawn as height and colour.
#' @param title,subtitle,caption Frame texts; the title defaults to `z`'s.
#' @param x_title,y_title,z_title Axis titles; `z_title` also names the
#'   colour key. They default to the column names as words.
#' @param colors A ramp name (see [hl_palettes()]); a brand's sequential
#'   ramp, else `"blues"`, by default.
#' @param percent Read `z` as shares and label it in percent.
#' @param gradient Blend each cell's colour along the ramp instead of
#'   binning it into bands; the key then shows the ramp at each tick.
#' @param heatmap Draw the values as a heatmap beside the surface, in the
#'   same colours: the surface shows the shape, the heatmap the values.
#'   Pointing at either in the HTML export marks the same grid point in both.
#'   It is saved at the double size unless [hl_save()] names another.
#' @param elevation,azimuth The viewpoint in degrees: height above the
#'   floor (10 to 80) and turn about the vertical axis.
#' @return A ggplot with the hairline frame.
#' @examples
#' grid <- expand.grid(hour = seq(6, 22, 1), week = 1:12)
#' grid$share <- 0.3 + 0.5 * exp(-((grid$hour - 12) / 3)^2)
#' hl_surface(grid, "hour", "week", "share", percent = TRUE)
#' @export
hl_surface <- function(data, x, y, z, title = NULL, subtitle = NULL, caption = NULL, x_title = NULL,
                       y_title = NULL, z_title = NULL, colors = NULL, percent = FALSE, gradient = FALSE,
                       heatmap = FALSE, elevation = NULL, azimuth = NULL) {
  titles <- list(x = x_title %||% humanise(x), y = y_title %||% humanise(y), z = z_title %||% humanise(z))
  spec <- surface_spec(data, x, y, z, titles, colors, percent, gradient, heatmap,
                       surface_checked_view(elevation, azimuth))
  key <- spec$key
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title %||% titles$z, subtitle = subtitle, caption = caption, x = NULL, y = NULL) +
    theme_hairline(axes = FALSE) + hl_legend(list()) +
    hl_legend_ramp(key$colors, key$steps, titles$z, format = if (percent) "percent" else "number",
                   limits = key$limits)
  plot@meta$hairline_drawing <- surface_drawing(spec)
  if (heatmap) plot@meta$hairline_size <- "double"
  plot@meta$hairline_surface <- spec
  plot@meta$hairline_description <- spec$description
  plot@meta$hairline_fit_height <- TRUE
  plot
}
