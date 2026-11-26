# One value over a grid of two numeric axes, shared by the surface and the heatmap, mirroring the Python
# charts/grid_values.py: reading the grid, the colour scale (bands or a gradient) with its key, and the texts a pointer
# reads.

# Values with the shared digits rule (percentages for shares). As Python's value_texts().
grid_value_texts <- function(values, percent) {
  values <- as.numeric(values)
  if (percent) {
    digits <- auto_digits(values * 100)
    return(vapply(values, function(value) hl_format_percent(snap_noise(value), digits), ""))
  }
  digits <- auto_digits(values)
  vapply(values, function(value) hl_format_number(snap_noise(value), digits), "")
}

# Every (x, y) pair once, or an error naming the first repeated one.
grid_check_pairs <- function(rows, x, y, z, chart) {
  pairs <- paste(rows[[x]], rows[[y]])
  repeated <- rows[pairs %in% pairs[duplicated(pairs)], , drop = FALSE]
  if (nrow(repeated)) {
    stop(sprintf(paste("hairline: %s: %d rows share an (%s, %s) pair, such as (%g, %g); give one '%s' per pair",
                       "(aggregate first)"), chart, nrow(repeated), x, y, repeated[[x]][1], repeated[[y]][1], z),
         call. = FALSE)
  }
}

# The distinct x and y values in order and z on their grid (rows y, columns x). As Python's read_grid().
read_grid <- function(data, x, y, z, chart) {
  check_columns(data, c(x, y, z))
  check_numeric(data, c(x, y, z), chart)
  for (column in c(x, y)) check_present(data, column, chart)
  rows <- data[!is.na(data[[x]]) & !is.na(data[[y]]), c(x, y, z), drop = FALSE]
  grid_check_pairs(rows, x, y, z, chart)
  xs <- sort(unique(as.numeric(rows[[x]])))
  ys <- sort(unique(as.numeric(rows[[y]])))
  most <- hl_tokens()$surface$max_side
  for (column in c(x, y)) {
    count <- length(if (column == x) xs else ys)
    if (count < 2 || count > most) {
      stop(sprintf("hairline: %s: '%s' needs 2 to %d distinct values for a grid; got %d%s", chart, column, most,
                   count, if (count > most) "; bin it first" else ""), call. = FALSE)
    }
  }
  grid <- matrix(NA_real_, length(ys), length(xs))
  grid[cbind(match(rows[[y]], ys), match(rows[[x]], xs))] <- as.numeric(rows[[z]])
  if (!any(is.finite(grid))) {
    stop(sprintf("hairline: %s: '%s' is missing in every row; there is nothing to colour", chart, z), call. = FALSE)
  }
  list(xs = xs, ys = ys, grid = grid)
}

# A colour per step: a sequential ramp without its lightest colour, a diverging ramp from pole to pole. As Python's
# step_colors().
grid_step_colours <- function(colors, count) {
  name <- colors %||% default_ramp("sequential")
  if (ramp_kind(name) == "diverging") hl_ramp(name, count) else hl_ramp(name, count + 1)[-1]
}

# The upper edges of the colour bins, up past the highest value: half a tick step each while that keeps the key to
# `max_bins` squares, a whole tick step otherwise. As Python's color_steps().
grid_colour_steps <- function(breaks, high) {
  for (share in c(0.5, 1)) {
    width <- (breaks[2] - breaks[1]) * share
    count <- max(1, ceiling((high - breaks[1]) / width - 1e-9))
    if (count <= hl_tokens()$surface$max_bins || share == 1) return(signif(breaks[1] + seq_len(count) * width, 10))
  }
}

# The colour of `value` among `count` blended from the axis's low to its high limit (1-based). As Python's
# ramp_position().
grid_ramp_position <- function(value, limits, count) {
  share <- (value - limits[1]) / (limits[2] - limits[1])
  min(count, max(1, floor(share * (count - 1) + 0.5) + 1))
}

# How values become colours, and the key in the legend row: bands by default, a blend along the ramp keyed at each
# tick with `gradient`. As Python's color_scale().
grid_colour_scale <- function(grid, breaks, colors, gradient) {
  low <- min(grid, na.rm = TRUE)
  high <- max(grid, na.rm = TRUE)
  rules <- hl_tokens()$surface
  if (gradient) {
    limits <- c(min(low, breaks[1]), max(high, breaks[length(breaks)]))
    blend <- grid_step_colours(colors, rules$gradient_steps)
    steps <- if (length(breaks) <= rules$max_bins) breaks else breaks[seq(1, length(breaks), by = 2)]
    key <- blend[vapply(steps, grid_ramp_position, 0, limits = limits, count = length(blend))]
    return(list(blend = blend, limits = limits, key = list(colors = key, steps = steps, limits = limits)))
  }
  steps <- grid_colour_steps(breaks, high)
  colours <- grid_step_colours(colors, length(steps))
  limits <- c(min(low, breaks[1]), max(high, breaks[length(breaks)], steps[length(steps)]))
  list(colours = colours, steps = steps, key = list(colors = colours, steps = steps, limits = limits))
}

# The colour of each value on the scale; NULL where it is missing. As Python's fills().
grid_fills <- function(values, scale) {
  colour <- function(value) {
    if (!is.null(scale$blend)) return(scale$blend[grid_ramp_position(value, scale$limits, length(scale$blend))])
    scale$colours[step_index(value, scale$steps)]
  }
  lapply(seq_len(nrow(values)), function(row) {
    lapply(values[row, ], function(value) if (is.finite(value)) colour(value) else NULL)
  })
}

# Each cell between four grid points: the mean of its corners. As Python's corner_means().
grid_corner_means <- function(grid) {
  rows <- nrow(grid)
  columns <- ncol(grid)
  (grid[-rows, -columns, drop = FALSE] + grid[-rows, -1, drop = FALSE] + grid[-1, -1, drop = FALSE] +
     grid[-1, -columns, drop = FALSE]) / 4
}

# What a pointer reads at each grid point: its x, its y and its value. As Python's grid_tips().
grid_tips <- function(xs, ys, grid, percent) {
  known <- grid[is.finite(grid)]
  digits <- auto_digits(if (percent) known * 100 else known)
  write <- if (percent) function(value) hl_format_percent(snap_noise(value), digits) else
    function(value) hl_format_number(snap_noise(value), digits)
  list(x = as.list(grid_value_texts(xs, FALSE)), y = as.list(grid_value_texts(ys, FALSE)),
       z = lapply(seq_len(nrow(grid)), function(row) {
         lapply(grid[row, ], function(value) if (is.finite(value)) write(value) else "")
       }))
}

# Round values within low to high, each placed by `place(value)`. As Python's inner_ticks().
grid_inner_ticks <- function(low, high, place) {
  breaks <- nice_breaks(low, high, hl_tokens()$surface$ticks)
  inside <- breaks[breaks >= low - 1e-9 & breaks <= high + 1e-9]
  texts <- grid_value_texts(inside, FALSE)
  lapply(seq_along(inside), function(k) list(at = place(inside[k]), text = texts[[k]]))
}
