# Heatmap, mirroring the Python charts/heatmap.py: one value over two numeric axes as a grid of cells, one per (x, y)
# pair, coloured in the bands of a ramp (or blended along it) and keyed in the legend row.

heatmap_chart <- "heatmap"

# Where the cells of sorted values meet: halfway between neighbours, half a step past the first and last. As Python's
# cell_edges().
heatmap_cell_edges <- function(values) {
  count <- length(values)
  c(values[1] - (values[2] - values[1]) / 2, (values[-count] + values[-1]) / 2,
    values[count] + (values[count] - values[count - 1]) / 2)
}

# Round values within the axis's range, placed on 0 to 1 from its first to its last cell edge. As Python's
# edge_ticks().
heatmap_edge_ticks <- function(values, edges) {
  low <- edges[1]
  high <- edges[length(edges)]
  grid_inner_ticks(values[1], values[length(values)], function(tick) (tick - low) / (high - low))
}

# The heatmap's part of a spec: cell edges on 0 to 1, each point's colour, ticks, titles and tooltip texts. As
# Python's flat_spec().
heatmap_flat_spec <- function(xs, ys, grid, scale, titles, percent) {
  x_edges <- heatmap_cell_edges(xs)
  y_edges <- heatmap_cell_edges(ys)
  unit <- function(edges) as.list((edges - edges[1]) / (edges[length(edges)] - edges[1]))
  list(x_edges = unit(x_edges), y_edges = unit(y_edges), fills = grid_fills(grid, scale),
       ticks = list(x = heatmap_edge_ticks(xs, x_edges), y = heatmap_edge_ticks(ys, y_edges)), titles = titles,
       tips = grid_tips(xs, ys, grid, percent), key = scale$key)
}

# Everything the heatmap draws, independent of the font. As Python's heatmap_spec().
heatmap_spec <- function(data, x, y, z, titles, colors = NULL, percent = FALSE, gradient = FALSE) {
  found <- read_grid(data, x, y, z, heatmap_chart)
  grid <- found$grid
  breaks <- nice_breaks(min(grid, na.rm = TRUE), max(grid, na.rm = TRUE), hl_tokens()$surface$ticks)
  spec <- heatmap_flat_spec(found$xs, found$ys, grid, grid_colour_scale(grid, breaks, colors, gradient), titles,
                            percent)
  spec$description <- alt_described("kind_heatmap", alt_grid_extremes(grid, spec$tips, titles))
  spec
}

#' Heatmap
#'
#' `z` over a grid of `x` and `y` (one row per pair; a pair without a row
#' is left blank) as one cell per pair, its value binned into the steps of
#' the ramp `colors` (or blended along it with `gradient = TRUE`) and keyed
#' in the legend row. In the HTML export a row highlights as one series and
#' each cell names its x, y and value. [hl_surface()] with
#' `heatmap = TRUE` draws it beside a 3D surface of the same values.
#'
#' @param data A data frame with one row per (`x`, `y`) pair.
#' @param x,y Numeric columns across and up.
#' @param z The numeric column drawn as colour.
#' @param title,subtitle,caption Frame texts; the title defaults to `z`'s.
#' @param x_title,y_title,z_title Axis titles; `z_title` names the colour
#'   key. They default to the column names as words.
#' @param colors A ramp name (see [hl_palettes()]); a brand's sequential
#'   ramp, else `"blues"`, by default.
#' @param percent Read `z` as shares and label it in percent.
#' @param gradient Blend each cell's colour along the ramp instead of
#'   binning it into bands; the key then shows the ramp at each tick.
#' @return A ggplot with the hairline frame.
#' @examples
#' grid <- expand.grid(hour = seq(6, 22, 1), week = 1:12)
#' grid$share <- 0.3 + 0.5 * exp(-((grid$hour - 12) / 3)^2)
#' hl_heatmap(grid, "hour", "week", "share", percent = TRUE)
#' @export
hl_heatmap <- function(data, x, y, z, title = NULL, subtitle = NULL, caption = NULL, x_title = NULL,
                       y_title = NULL, z_title = NULL, colors = NULL, percent = FALSE, gradient = FALSE) {
  titles <- list(x = x_title %||% humanise(x), y = y_title %||% humanise(y), z = z_title %||% humanise(z))
  spec <- heatmap_spec(data, x, y, z, titles, colors, percent, gradient)
  key <- spec$key
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title %||% titles$z, subtitle = subtitle, caption = caption, x = NULL, y = NULL) +
    theme_hairline(axes = FALSE) + hl_legend(list()) +
    hl_legend_ramp(key$colors, key$steps, titles$z, format = if (percent) "percent" else "number",
                   limits = key$limits)
  plot@meta$hairline_drawing <- function(box, measure, style) heatmap_shapes(heatmap_scene(spec, measure, style), box)
  plot@meta$hairline_description <- spec$description
  plot@meta$hairline_fit_height <- TRUE
  plot
}
