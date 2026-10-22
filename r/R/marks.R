# Series colours, the light-slot treatment and point density, applied to built layer data.

series_colors <- function(categories, palette_name = NULL) {
  stats::setNames(hl_palette(palette_name, n = length(categories)), categories)
}

# Checked once per distinct colour: built layer data repeats a series' colour on every row.
is_light_colour <- function(colours, surface) {
  limit <- hl_tokens()$checks$contrast_light_slot
  distinct <- unique(colours)
  light <- vapply(distinct, function(colour) {
    !is.na(colour) && grepl("^#[0-9a-fA-F]{6}$", colour) && contrast_ratio(colour, surface) < limit
  }, logical(1))
  stats::setNames(light[match(colours, distinct)], colours)
}

surface_colour <- function(settings) {
  if (identical(settings$background, "transparent")) "#ffffff" else settings$neutral$surface
}

# The colour itself, or a shade of its hue that reaches 3:1 against the surface: darker on a light surface, lighter
# on a dark one.
point_fill <- function(colour, surface) {
  limit <- hl_tokens()$checks$contrast_light_slot
  step <- hl_tokens()$points$fill_lightness_step
  values <- hex_to_oklch(colour)
  direction <- if (hex_to_oklch(surface)[1] >= 0.5) -1 else 1
  fill <- colour
  while (contrast_ratio(fill, surface) < limit && values[1] > 0 && values[1] < 1) {
    values[1] <- min(1, max(0, values[1] + direction * step))
    fill <- oklch_to_hex(values[1], values[2], values[3])
  }
  fill
}

# Colour of a lone series (a chart without groups): the accent, made readable on the surface, else slot 1.
lone_colour <- function(settings = hl_settings()) {
  if (is.null(settings$accent)) settings$palette[1] else point_fill(settings$accent, surface_colour(settings))
}

# Grey for series that recede (highlight), lighter than ink on light surfaces, darker on dark ones.
context_colour <- function(settings = hl_settings()) {
  hl_tokens()$focus[[if (identical(settings$scheme, "dark")) "context_dark" else "context"]]
}

point_step <- function(count) {
  steps <- hl_tokens()$points$steps
  for (index in seq_len(nrow(steps))) {
    if (is.na(steps$max[index]) || count <= steps$max[index]) {
      return(c(radius = steps$radius[index], opacity = steps$opacity[index]))
    }
  }
  stop("hairline: tokens points.steps needs a last step with max null", call. = FALSE)
}

adjust_line_layer <- function(data, light) {
  data$linewidth[light] <- data$linewidth[light] * hl_tokens()$lines$light_slot_line
  data
}

layer_sets <- function(layer, plot, aesthetic) {
  mapped <- names(c(layer$mapping, if (isTRUE(layer$inherit.aes)) plot@mapping))
  aesthetic %in% c(names(layer$aes_params), mapped)
}

adjust_point_layer <- function(data, light, layer, plot) {
  default_shape <- data$shape %in% c(16, 19)
  targets <- default_shape & light
  surface <- surface_colour(hl_settings())
  distinct <- unique(data$colour[targets])
  fills <- vapply(distinct, point_fill, character(1), surface = surface)
  data$colour[targets] <- fills[match(data$colour[targets], distinct)]
  data$fill[default_shape] <- data$colour[default_shape]
  data$stroke[default_shape] <- 0
  data$shape[default_shape] <- 16
  steps <- vapply(as.vector(table(data$PANEL)[as.character(data$PANEL)]), point_step, numeric(2))
  if (!layer_sets(layer, plot, "size")) data$size <- pt_to_mm(2 * steps["radius", ] * hl_settings()$base_size / 0.75)
  if (!layer_sets(layer, plot, "alpha")) data$alpha <- ifelse(is.na(data$alpha), steps["opacity", ], data$alpha)
  data
}

apply_light_slots <- function(built) {
  settings <- hl_settings()
  surface <- surface_colour(settings)
  for (index in seq_along(built@data)) {
    data <- built@data[[index]]
    geom <- class(built@plot@layers[[index]]$geom)[1]
    if (!"colour" %in% names(data) || isTRUE(built@plot@layers[[index]]$hairline_secondary)) next
    light <- is_light_colour(data$colour, surface) & !(data$.hairline_context %||% FALSE)
    if (geom %in% c("GeomLine", "GeomPath", "GeomStep") && "linewidth" %in% names(data)) {
      data <- adjust_line_layer(data, light)
    } else if (geom == "GeomPoint") {
      data <- adjust_point_layer(data, light, built@plot@layers[[index]], built@plot)
    }
    built@data[[index]] <- data
  }
  built
}

# Data lines thin out on narrower panels: the step for a plot box `width_pt` wide.
line_scale <- function(width_pt) {
  width_mm <- width_pt * 25.4 / 72
  steps <- hl_tokens()$lines$panel_steps
  for (index in seq_len(nrow(steps))) {
    if (is.na(steps$max_mm[index]) || width_mm <= steps$max_mm[index]) return(steps$scale[index])
  }
  stop("hairline: tokens lines.panel_steps needs a last step with max_mm null", call. = FALSE)
}

# Which layers draw data lines; structural ones (references, medians, brackets) keep their width.
line_layers <- function(built) {
  vapply(built@plot@layers, function(layer) {
    class(layer$geom)[1] %in% c("GeomLine", "GeomPath", "GeomStep") && !isTRUE(layer$hairline_fixed)
  }, logical(1))
}

scale_grob_lines <- function(grob, scale) {
  if (!is.null(grob$gp$lwd)) grob$gp$lwd <- grob$gp$lwd * scale
  if (inherits(grob, "gTree")) {
    grob <- grid::setChildren(grob, do.call(grid::gList, lapply(grob$children, scale_grob_lines, scale = scale)))
  }
  grob
}

# A ggplot panel lists the grid, the background and then one grob per layer, in layer order.
scale_layer_lines <- function(panel, layers, scale) {
  first <- which(startsWith(names(panel$children), "grill"))[1] + 2
  if (is.na(first) || first + length(layers) - 1 > length(panel$children) || scale == 1) return(panel)
  children <- panel$children
  for (index in which(layers)) children[[first + index - 1]] <- scale_grob_lines(children[[first + index - 1]], scale)
  grid::setChildren(panel, children)
}
