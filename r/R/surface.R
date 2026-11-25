# Surface, mirroring the Python charts/surface.py: one value over two numeric axes drawn as a turned 3D surface from a
# fixed viewpoint, its height binned into the steps of a ramp and keyed in the legend row. Turnable in the HTML export.

surface_chart <- "surface"

# Values with the shared digits rule (percentages for shares). As Python's value_texts().
surface_value_texts <- function(values, percent) {
  values <- as.numeric(values)
  if (percent) {
    digits <- auto_digits(values * 100)
    return(vapply(values, function(value) hl_format_percent(snap_noise(value), digits), ""))
  }
  digits <- auto_digits(values)
  vapply(values, function(value) hl_format_number(snap_noise(value), digits), "")
}

# The distinct x and y values in order and z on their grid (rows y, columns x). As Python's surface_grid().
surface_grid <- function(data, x, y, z) {
  check_columns(data, c(x, y, z))
  check_numeric(data, c(x, y, z), surface_chart)
  for (column in c(x, y)) check_present(data, column, surface_chart)
  rows <- data[!is.na(data[[x]]) & !is.na(data[[y]]), c(x, y, z), drop = FALSE]
  pairs <- paste(rows[[x]], rows[[y]])
  repeated <- rows[pairs %in% pairs[duplicated(pairs)], , drop = FALSE]
  if (nrow(repeated)) {
    stop(sprintf(paste("hairline: %s: %d rows share an (%s, %s) pair, such as (%g, %g); give one '%s' per pair",
                       "(aggregate first)"), surface_chart, nrow(repeated), x, y, repeated[[x]][1], repeated[[y]][1],
                 z), call. = FALSE)
  }
  xs <- sort(unique(as.numeric(rows[[x]])))
  ys <- sort(unique(as.numeric(rows[[y]])))
  most <- hl_tokens()$surface$max_side
  for (column in c(x, y)) {
    count <- length(if (column == x) xs else ys)
    if (count < 2 || count > most) {
      stop(sprintf("hairline: %s: '%s' needs 2 to %d distinct values for a grid; got %d%s", surface_chart, column,
                   most, count, if (count > most) "; bin it first" else ""), call. = FALSE)
    }
  }
  grid <- matrix(NA_real_, length(ys), length(xs))
  grid[cbind(match(rows[[y]], ys), match(rows[[x]], xs))] <- as.numeric(rows[[z]])
  list(xs = xs, ys = ys, grid = grid)
}

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

# A colour per step: a sequential ramp without its lightest colour, a diverging ramp from pole to pole. As Python's
# step_colors().
surface_step_colours <- function(colors, count) {
  name <- colors %||% default_ramp("sequential")
  if (ramp_kind(name) == "diverging") hl_ramp(name, count) else hl_ramp(name, count + 1)[-1]
}

# The colour of `value` among `count` blended from the axis's low to its high limit. As Python's ramp_position().
surface_ramp_position <- function(value, limits, count) {
  share <- (value - limits[1]) / (limits[2] - limits[1])
  min(count, max(1, floor(share * (count - 1) + 0.5) + 1))
}

# The key of a gradient: the ramp's colour at each tick (every other tick past `max_bins`). As Python's
# gradient_key().
surface_gradient_key <- function(breaks, limits, colours) {
  steps <- if (length(breaks) <= hl_tokens()$surface$max_bins) breaks else breaks[seq(1, length(breaks), by = 2)]
  list(colors = colours[vapply(steps, surface_ramp_position, 0, limits = limits, count = length(colours))],
       steps = steps, limits = limits)
}

# Each cell's colour: its corners' mean on the ramp blended between the axis's limits. As Python's gradient_fills().
surface_gradient_fills <- function(grid, limits, colours) {
  rows <- nrow(grid)
  columns <- ncol(grid)
  means <- (grid[-rows, -columns, drop = FALSE] + grid[-rows, -1, drop = FALSE] + grid[-1, -1, drop = FALSE] +
              grid[-1, -columns, drop = FALSE]) / 4
  lapply(seq_len(rows - 1), function(row) {
    lapply(seq_len(columns - 1), function(column) {
      mean <- means[row, column]
      if (is.finite(mean)) colours[surface_ramp_position(mean, limits, length(colours))] else NULL
    })
  })
}

# The cells' colours and the key: bands by default, a blend along the ramp with `gradient`. As Python's
# surface_colors().
surface_colours <- function(grid, breaks, colors, gradient) {
  low <- min(grid, na.rm = TRUE)
  high <- max(grid, na.rm = TRUE)
  if (gradient) {
    limits <- c(min(low, breaks[1]), max(high, breaks[length(breaks)]))
    blend <- surface_step_colours(colors, hl_tokens()$surface$gradient_steps)
    return(list(fills = surface_gradient_fills(grid, limits, blend), key = surface_gradient_key(breaks, limits, blend)))
  }
  steps <- surface_colour_steps(breaks, high)
  limits <- c(min(low, breaks[1]), max(high, breaks[length(breaks)], steps[length(steps)]))
  colours <- surface_step_colours(colors, length(steps))
  list(fills = surface_cell_fills(grid, steps, colours), key = list(colors = colours, steps = steps, limits = limits))
}

# The upper edges of the colour bins, up past the highest value: half a tick step each while that keeps the key to
# `max_bins` squares, a whole tick step otherwise. As Python's color_steps().
surface_colour_steps <- function(breaks, high) {
  for (share in c(0.5, 1)) {
    width <- (breaks[2] - breaks[1]) * share
    count <- max(1, ceiling((high - breaks[1]) / width - 1e-9))
    if (count <= hl_tokens()$surface$max_bins || share == 1) return(signif(breaks[1] + seq_len(count) * width, 10))
  }
}

# Each cell's colour: the step its corners' mean falls in; NULL for a cell with a corner missing. As Python's
# cell_fills().
surface_cell_fills <- function(grid, steps, colours) {
  rows <- nrow(grid)
  columns <- ncol(grid)
  means <- (grid[-rows, -columns, drop = FALSE] + grid[-rows, -1, drop = FALSE] + grid[-1, -1, drop = FALSE] +
              grid[-1, -columns, drop = FALSE]) / 4
  lapply(seq_len(rows - 1), function(row) {
    lapply(seq_len(columns - 1), function(column) {
      mean <- means[row, column]
      if (is.finite(mean)) colours[step_index(mean, steps)] else NULL
    })
  })
}

# Round values within the axis's range, placed on the cube's -1 to 1. As Python's axis_ticks().
surface_axis_ticks <- function(values, target) {
  low <- min(values)
  high <- max(values)
  breaks <- nice_breaks(low, high, target)
  inside <- breaks[breaks >= low - 1e-9 & breaks <= high + 1e-9]
  texts <- surface_value_texts(inside, FALSE)
  lapply(seq_along(inside), function(k) list(at = 2 * (inside[k] - low) / (high - low) - 1, text = texts[[k]]))
}

# The value axis's breaks, placed on the cube's height (centred on zero). As Python's height_ticks().
surface_height_ticks <- function(breaks, limits, height, percent) {
  texts <- surface_value_texts(breaks, percent)
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

# What a pointer on the surface reads in the HTML export: each grid point's x, y and value. As Python's vertex_tips().
surface_vertex_tips <- function(xs, ys, grid, percent) {
  known <- grid[is.finite(grid)]
  digits <- auto_digits(if (percent) known * 100 else known)
  write <- if (percent) function(value) hl_format_percent(snap_noise(value), digits) else
    function(value) hl_format_number(snap_noise(value), digits)
  list(x = as.list(surface_value_texts(xs, FALSE)), y = as.list(surface_value_texts(ys, FALSE)),
       z = lapply(seq_len(nrow(grid)), function(row) {
         lapply(grid[row, ], function(value) if (is.finite(value)) write(value) else "")
       }))
}

# Everything the drawing needs, independent of the font. As Python's surface_spec().
surface_spec <- function(data, x, y, z, titles, colors = NULL, percent = FALSE, gradient = FALSE, view = NULL) {
  found <- surface_grid(data, x, y, z)
  xs <- found$xs
  ys <- found$ys
  grid <- found$grid
  surface_check_cells(grid, z)
  rules <- hl_tokens()$surface
  breaks <- nice_breaks(min(grid, na.rm = TRUE), max(grid, na.rm = TRUE), rules$ticks)
  coloured <- surface_colours(grid, breaks, colors, gradient)
  limits <- coloured$key$limits
  height <- rules$height
  normal <- height * ((grid - limits[1]) / (limits[2] - limits[1]) - 0.5)
  list(xs = as.list(2 * (xs - xs[1]) / (xs[length(xs)] - xs[1]) - 1),
       ys = as.list(2 * (ys - ys[1]) / (ys[length(ys)] - ys[1]) - 1),
       zs = lapply(seq_len(nrow(normal)), function(row) {
         lapply(normal[row, ], function(value) if (is.finite(value)) value else NULL)
       }),
       fills = coloured$fills, height = height,
       view = view %||% surface_checked_view(NULL, NULL),
       ticks = list(x = surface_axis_ticks(xs, rules$ticks), y = surface_axis_ticks(ys, rules$ticks),
                    z = surface_height_ticks(breaks, limits, height, percent)),
       titles = titles, key = coloured$key,
       tips = surface_vertex_tips(xs, ys, grid, percent))
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
                       elevation = NULL, azimuth = NULL) {
  titles <- list(x = x_title %||% humanise(x), y = y_title %||% humanise(y), z = z_title %||% humanise(z))
  spec <- surface_spec(data, x, y, z, titles, colors, percent, gradient, surface_checked_view(elevation, azimuth))
  key <- spec$key
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title %||% titles$z, subtitle = subtitle, caption = caption, x = NULL, y = NULL) +
    theme_hairline(axes = FALSE) + hl_legend(list()) +
    hl_legend_ramp(key$colors, key$steps, titles$z, format = if (percent) "percent" else "number",
                   limits = key$limits)
  plot@meta$hairline_drawing <- function(box, measure, style) {
    surface_scene_shapes(surface_scene(spec, measure, style), box)
  }
  plot@meta$hairline_surface <- spec
  plot@meta$hairline_fit_height <- TRUE
  plot
}
