# Series colours, the light-slot treatment and point density, applied to built layer data.

series_colors <- function(categories, palette_name = NULL) {
  stats::setNames(hl_palette(palette_name, n = length(categories)), categories)
}

is_light_colour <- function(colours, surface) {
  limit <- hl_tokens()$checks$contrast_light_slot
  vapply(colours, function(colour) {
    !is.na(colour) && grepl("^#[0-9a-fA-F]{6}$", colour) && contrast_ratio(colour, surface) < limit
  }, logical(1))
}

surface_colour <- function(settings) {
  if (identical(settings$background, "transparent")) "#ffffff" else settings$neutral$surface
}

point_fill <- function(colour, surface) {
  limit <- hl_tokens()$checks$contrast_light_slot
  step <- hl_tokens()$points$fill_lightness_step
  values <- hex_to_oklch(colour)
  fill <- colour
  while (contrast_ratio(fill, surface) < limit && values[1] > 0) {
    values[1] <- max(0, values[1] - step)
    fill <- oklch_to_hex(values[1], values[2], values[3])
  }
  fill
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
  data$colour[targets] <- vapply(data$colour[targets], point_fill, character(1), surface = surface)
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
