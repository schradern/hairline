# Scatter density: the points counted in a grid of hexagons, each coloured by its count in the bins of a ramp and
# keyed in the legend row, for clouds too dense to read point by point. Pointy-top hexagons, `bins` across the x
# range and as many rows as keep them regular on the plot they fill: `density$aspect` as tall as it is wide alone, a
# grid of panels times its columns over its rows. Mirrors the Python package's charts/scatter_density.py.

density_root3 <- sqrt(3)

# Hexagons across the x range: the token's with `density = TRUE`, the number given, or NULL for points. As Python's
# density_bins().
density_bins <- function(density, chart) {
  if (is.null(density) || isFALSE(density)) return(NULL)
  rules <- hl_tokens()$density
  if (isTRUE(density)) return(as.integer(rules$bins))
  whole <- is.numeric(density) && length(density) == 1 && is.finite(density) && density == round(density)
  if (!whole || density < rules$min_bins) {
    stop(sprintf(paste("hairline: %s: density must be TRUE, FALSE or a whole number of hexagons across of at least",
                       "%d; got %s"), chart, as.integer(rules$min_bins), format(density)), call. = FALSE)
  }
  as.integer(density)
}

# The lattice over every point drawn: its origin (the lowest x and y), the spacing of hexagon centres in a row and
# between rows, in data units; `shape` the panels' columns and rows. As Python's hex_grid().
density_grid <- function(x, y, bins, chart, shape = c(1, 1)) {
  x_range <- max(x) - min(x)
  y_range <- max(y) - min(y)
  if (!(x_range > 0 && y_range > 0)) {
    stop(sprintf(paste("hairline: %s: density needs points spread along both axes; got an x range of %s and a y",
                       "range of %s; use density = FALSE for the points alone"), chart, format(x_range),
                 format(y_range)), call. = FALSE)
  }
  list(x0 = min(x), y0 = min(y), width = x_range / bins,
       height = density_root3 / 2 * y_range / (bins * hl_tokens()$density$aspect * shape[1] / shape[2]))
}

# Each point's hexagon as (row, column): the nearer of the centres on the even and the odd rows, measured on the
# regular lattice; a point as near to both takes the even row. As Python's nearest_cells().
density_nearest <- function(x, y, grid) {
  across <- (x - grid$x0) / grid$width
  up <- (y - grid$y0) / grid$height
  even_row <- 2 * floor(up / 2 + 0.5)
  even_column <- floor(across + 0.5)
  odd_row <- 2 * floor((up - 1) / 2 + 0.5) + 1
  odd_column <- floor(across)
  even <- round((across - even_column)^2 + ((up - even_row) * density_root3 / 2)^2, alt_tie_digits)
  odd <- round((across - odd_column - 0.5)^2 + ((up - odd_row) * density_root3 / 2)^2, alt_tie_digits)
  nearer <- even <= odd
  list(row = as.integer(ifelse(nearer, even_row, odd_row)), column = as.integer(ifelse(nearer, even_column,
                                                                                         odd_column)))
}

# The hexagons with points, bottom row first and left to right: row, column, centre and count. As Python's
# hex_counts().
density_counts <- function(x, y, grid) {
  if (!length(x)) return(list())
  cells <- density_nearest(x, y, grid)
  found <- unique(data.frame(row = cells$row, column = cells$column))
  found <- found[order(found$row, found$column), , drop = FALSE]
  keys <- paste(cells$row, cells$column)
  lapply(seq_len(nrow(found)), function(index) {
    row <- found$row[index]
    column <- found$column[index]
    list(row = row, column = column, count = sum(keys == paste(row, column)),
         x = grid$x0 + (column + (row %% 2) / 2) * grid$width, y = grid$y0 + row * grid$height)
  })
}

# A hexagon's six corners from the top, clockwise, as a two-column matrix. As Python's hex_corners().
density_corners <- function(cell, grid) {
  half <- grid$width / 2
  third <- grid$height / 3
  cbind(cell$x + c(0, half, half, 0, -half, -half), cell$y + c(2, 1, -1, -2, -1, 1) * third)
}

# The upper edges of the colour bins for counts up to `top`: whole round steps from the first past zero up to `top`
# or beyond, at most `density$max_bins` of them. As Python's count_steps().
density_steps <- function(top) {
  most <- hl_tokens()$density$max_bins
  breaks <- nice_breaks(0, top, hl_tokens()$surface$ticks, whole = TRUE)
  step <- max(1, breaks[2] - breaks[1])
  while (ceiling(top / step - 1e-9) > most) step <- step * 2
  step * seq_len(ceiling(top / step - 1e-9))
}

# The bins of the counts, a colour for each from the ramp `colors`, and the legend row's key. As Python's
# density_scale().
density_scale <- function(counts, colors) {
  steps <- density_steps(max(counts))
  colours <- grid_step_colours(colors, length(steps))
  list(steps = steps, colours = colours, key = list(colors = colours, steps = steps, limits = c(0, steps[length(steps)])))
}

# "1 point", "12 points": what a hexagon's tooltip reads. As Python's count_text().
density_count_text <- function(count) {
  if (count == 1) word("hexagon_one") else word("hexagon_many", n = hl_format_number(count, 0))
}

density_fill <- function(count, scale) scale$colours[step_index(count, scale$steps)]

# Hexagons count every point together and take their colours from one ramp. As Python's check_density().
density_check <- function(by, colors, highlight) {
  if (!is.null(by) || !is.null(highlight)) {
    stop(paste("hairline: scatter: density counts every point together, so it takes no by = or highlight =;",
               "use facet = for a panel per group"), call. = FALSE)
  }
  if (!is.null(colors) && !(is.character(colors) && length(colors) == 1 && is.null(names(colors)))) {
    stop(sprintf(paste("hairline: scatter: density colours its hexagons by a ramp; colors must be a ramp name such as",
                       "'blues'; got %s"), paste(format(colors), collapse = ", ")), call. = FALSE)
  }
}

# One lattice over the points drawn in every panel, so faceted panels share their hexagons and colours, and each
# panel's hexagons with their counts; `columns` panels to a row. As Python's density_cells().
density_cells <- function(shown, x, y, bins, colors, columns = 1) {
  every <- do.call(rbind, shown)
  shape <- c(min(columns, length(shown)), ceiling(length(shown) / columns))
  grid <- density_grid(every[[x]], every[[y]], bins, "scatter", shape)
  cells <- lapply(shown, function(rows) density_counts(rows[[x]], rows[[y]], grid))
  counts <- unlist(lapply(cells, function(panel) vapply(panel, `[[`, 0, "count")))
  list(grid = grid, panels = cells, peak = max(counts), scale = density_scale(counts, colors))
}

# One panel's hexagons as a polygon layer, edged in their own colour so no seam of the page shows between
# neighbours, and each a tooltip target naming its count.
density_layers <- function(hexagons, index) {
  cells <- hexagons$panels[[index]]
  corners <- lapply(cells, density_corners, grid = hexagons$grid)
  fills <- vapply(cells, function(cell) density_fill(cell$count, hexagons$scale), "")
  frame <- data.frame(x = unlist(lapply(corners, function(points) points[, 1])),
                      y = unlist(lapply(corners, function(points) points[, 2])),
                      cell = rep(seq_along(cells), each = 6), fill = rep(fills, each = 6))
  layer <- ggplot2::geom_polygon(data = frame, ggplot2::aes(.data$x, .data$y, group = .data$cell),
                                 fill = frame$fill, colour = frame$fill,
                                 linewidth = pt_to_linewidth(hl_tokens()$density$edge_pt), inherit.aes = FALSE)
  name <- word("density_key")
  targets <- lapply(seq_along(cells), function(cell) {
    chart_target(index, name, fills[cell], list(list(polygon = corners[[cell]])),
                 list(list(at = c(cells[[cell]]$x, cells[[cell]]$y), text = density_count_text(cells[[cell]]$count))))
  })
  list(layer = static_layer(layer), targets = targets)
}
