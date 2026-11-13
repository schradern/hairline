# Ridgeline drawing, mirroring the Python ridgeline_drawing.py: each ridge's fill and outline, its median line and
# mean diamond, spikes for a group without a density, and what each draws in data units for its tooltip targets.

# The most a plot grows (x its least height) to keep the bottom ridge's mean diamond inside it; a diamond lower still
# is lifted to the height that growth holds. As Python's MEAN_GROWTH.
ridge_mean_growth <- 2

# How far the mean diamond reaches from its centre, in base sizes: its half-diagonal and half its outline.
ridge_diamond_reach <- function() {
  lines <- hl_tokens()$lines
  diamond_size * lines$point_radius + lines$data * open_edge / 2
}

# The least height, in rows, of a bottom-row mean diamond above its baseline: where a plot grown ridge_mean_growth
# times its least height (`top` rows high) just holds it. As Python's mean_floor().
ridge_mean_floor <- function(top) {
  ridge_diamond_reach() * top / (ridge_mean_growth * hl_tokens()$spacing$min_plot_height)
}

# The least plot height (x the base size) at which each bottom-row mean diamond, `lifts` rows above its baseline,
# stays inside its panel (`top` rows high), for `panel_rows` rows of panels; NULL without one. As Python's
# mean_plot_height().
ridge_mean_plot_height <- function(lifts, top, panel_rows) {
  if (!length(lifts)) return(NULL)
  max(hl_tokens()$spacing$min_plot_height, ridge_diamond_reach() * top / min(lifts) * panel_rows)
}

# The layers and what they draw, for the ridge's tooltip targets: its fill and outline in data units, its centres
# and the median's top.
ridge_layers <- function(curve, values, base, scale, colour, marks, counted = values, floor = 0) {
  settings <- hl_settings()
  rules <- hl_tokens()$ridgeline
  outline <- data.frame(x = curve$grid, y = base + curve$height * scale)
  corners <- rbind(data.frame(x = curve$grid[1], y = base), outline,
                   data.frame(x = curve$grid[length(curve$grid)], y = base))
  width <- hl_tokens()$lines$data * settings$base_size
  layers <- list(ggplot2::geom_polygon(data = corners, ggplot2::aes(.data$x, .data$y), fill = settings$neutral$surface,
                                       colour = NA, inherit.aes = FALSE),
                 ggplot2::geom_polygon(data = corners, ggplot2::aes(.data$x, .data$y), fill = colour,
                                       alpha = rules$fill_opacity, colour = NA, inherit.aes = FALSE),
                 static_layer(ggplot2::geom_path(data = outline, ggplot2::aes(.data$x, .data$y), colour = colour,
                                                 linewidth = pt_to_linewidth(width), inherit.aes = FALSE)))
  marks_drawn <- list(list(polygon = as.matrix(corners), alpha = rules$fill_opacity),
                      list(line = as.matrix(outline), width = width))
  if (!length(counted)) return(list(layers = layers, marks = marks_drawn, top = NULL))
  centres <- ridge_centre_layers(counted, curve, base, scale, marks, colour, floor)
  list(layers = c(layers, centres$layers), marks = c(marks_drawn, centres$marks), top = centres$top)
}

# The median as a line from the baseline up to the ridge, the mean as an open diamond on the ridge's outline; both
# held within the ridge; with them in data units and the median's top. As Python's draw_centres().
ridge_centre_layers <- function(counted, curve, base, scale, marks, colour, floor = 0) {
  settings <- hl_settings()
  found <- summary_values(counted)
  on_ridge <- function(value) {
    x <- min(max(value, curve$grid[1]), curve$grid[length(curve$grid)])
    c(x, base + stats::approx(curve$grid, curve$height, x)$y * scale)
  }
  layers <- list()
  shapes <- list()
  top <- NULL
  if ("median" %in% marks) {
    top <- on_ridge(found$median)
    line <- hl_tokens()$reference$width * settings$base_size
    median <- ggplot2::geom_segment(data = data.frame(x = top[1], y = base, yend = top[2]),
                                    ggplot2::aes(.data$x, .data$y, xend = .data$x, yend = .data$yend),
                                    colour = settings$neutral$ink, inherit.aes = FALSE,
                                    linewidth = pt_to_linewidth(line))
    median$hairline_secondary <- TRUE
    layers <- c(layers, list(median))
    shapes <- c(shapes, list(list(line = rbind(c(top[1], base), top), width = line, color = settings$neutral$ink)))
  }
  if ("mean" %in% marks) {
    centre <- on_ridge(found$mean)
    centre[2] <- max(centre[2], base + floor)
    width <- hl_tokens()$lines$data * settings$base_size
    layers <- c(layers, list(mean_diamond(centre[1], centre[2], colour)))
    shapes <- c(shapes, list(list(diamond = centre,
                                  r = diamond_size * hl_tokens()$lines$point_radius * settings$base_size,
                                  color = settings$neutral$surface, edge = colour, edge_width = width * open_edge)))
  }
  list(layers = layers, marks = shapes, top = top)
}

# A group too small or too uniform for a density (one value, or all alike) shows each value as a spike, so its row is
# never empty.
ridge_spikes <- function(values, base, colour, rules) {
  shown <- sort(unique(as.numeric(values)))
  if (!length(shown)) return(list(layers = list(), marks = list(), top = NULL))
  width <- hl_tokens()$lines$data * hl_settings()$base_size
  spikes <- data.frame(x = shown, y = base, yend = base + rules$spike)
  list(layers = list(static_layer(ggplot2::geom_segment(data = spikes, ggplot2::aes(.data$x, .data$y, xend = .data$x,
                                                                                    yend = .data$yend),
                                                        colour = colour, linewidth = pt_to_linewidth(width),
                                                        inherit.aes = FALSE))),
       marks = lapply(shown, function(value) {
         list(line = rbind(c(value, base), c(value, base + rules$spike)), width = width)
       }),
       top = NULL)
}

# Where a ridge's tooltip points: the top of its median line, else the highest point of its outline (or of its
# spikes). As Python's ridge_anchor().
ridge_anchor <- function(marks, top) {
  if (!is.null(top)) return(top)
  points <- do.call(rbind, lapply(Filter(function(mark) !is.null(mark$line), marks), `[[`, "line"))
  points[which.max(points[, 2]), ]
}

# One panel's ridges, top row first, each lower ridge in front of the one above; a group without a density shows its
# values as spikes. Returns the layers and each ridge drawn: its marks in data units and where its tooltip points.
ridgeline_panel_layers <- function(drawn, curves, counted, scale, marks, palette, floor = 0) {
  rules <- hl_tokens()$ridgeline
  names <- names(drawn)
  layers <- list()
  ridges <- list()
  for (index in seq_along(names)) {
    base <- length(names) - index
    ridge <- if (is.null(curves[[index]])) {
      ridge_spikes(drawn[[index]], base, palette[[names[index]]], rules)
    } else {
      ridge_layers(curves[[index]], drawn[[index]], base, scale, palette[[names[index]]], marks, counted[[index]],
                   if (base == 0) floor else 0)
    }
    layers <- c(layers, ridge$layers)
    if (length(ridge$marks)) {
      ridges[[names[index]]] <- list(marks = ridge$marks, at = ridge_anchor(ridge$marks, ridge$top))
    }
  }
  list(layers = layers, ridges = ridges)
}
