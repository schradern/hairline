# Legend row: items from the plot's discrete colour/fill scales, packed into rows that wrap.

legend_kind <- function(built, aesthetic) {
  for (layer in built@plot@layers) {
    mapped <- names(c(layer$mapping, if (isTRUE(layer$inherit.aes)) built@plot@mapping))
    if (!aesthetic %in% mapped && !(aesthetic == "colour" && "color" %in% mapped)) next
    geom <- class(layer$geom)[1]
    if (geom %in% c("GeomLine", "GeomPath", "GeomStep", "GeomSmooth")) return("line")
    if (geom == "GeomPoint") return("dot")
    return("square")
  }
  "square"
}

warn_unsupported_legend <- function(scale) {
  if (identical(scale$guide, "none") || any(scale$aesthetics %in% c("x", "y", "xmin", "xmax", "ymin", "ymax"))) {
    return(invisible())
  }
  warning(sprintf("hairline: the %s legend (%s) is not supported yet and was left out; label the mapping in the %s",
                  scale$aesthetics[1], if (scale$is_discrete()) "discrete" else "continuous",
                  "subtitle or caption"), call. = FALSE)
}

point_fills <- function(colours) {
  surface <- surface_colour(hl_settings())
  vapply(colours, function(colour) if (is_hex(colour)) point_fill(colour, surface) else colour, character(1),
         USE.NAMES = FALSE)
}

legend_items <- function(built) {
  items <- list()
  seen <- character()
  for (scale in built@plot@scales$scales) {
    aesthetic <- intersect(scale$aesthetics, c("colour", "fill"))[1]
    if (is.na(aesthetic) || !scale$is_discrete()) {
      warn_unsupported_legend(scale)
      next
    }
    breaks <- scale$get_breaks()
    labels <- scale$get_labels(breaks)
    colours <- scale$map(breaks)
    kind <- legend_kind(built, aesthetic)
    if (kind == "dot") colours <- point_fills(colours)
    highlighted <- built@plot@meta$hairline_highlight$series
    if (!is.null(highlighted)) colours[!labels %in% highlighted] <- hl_tokens()$focus$context
    for (index in seq_along(breaks)) {
      if (is.na(labels[index]) || labels[index] %in% seen) next
      seen <- c(seen, labels[index])
      items[[length(items) + 1]] <- list(kind = kind, colour = colours[index], label = labels[index])
    }
  }
  items
}

swatch_width <- function(kind, base, spacing) {
  factor <- if (kind %in% c("dot", "square")) spacing$legend_swatch_square else spacing$legend_swatch_line
  factor * base
}

pack_legend <- function(items, left, right, style, base, spacing) {
  row <- 0
  cursor <- left
  placed <- list()
  for (item in items) {
    width <- swatch_width(item$kind, base, spacing) + spacing$legend_swatch_text * base +
      text_width_pt(item$label, style)
    if (cursor > left && cursor + width > right) {
      row <- row + 1
      cursor <- left
    }
    placed[[length(placed) + 1]] <- c(item, list(row = row, x = cursor, right = cursor + width))
    cursor <- cursor + width + spacing$legend_item * base
  }
  placed
}

swatch_grob <- function(entry, center, height, base, spacing, lines) {
  width <- swatch_width(entry$kind, base, spacing)
  y <- height - center
  if (entry$kind == "thin") {
    return(grid::segmentsGrob(grid::unit(entry$x, "pt"), grid::unit(y, "pt"), grid::unit(entry$x + width, "pt"),
                              grid::unit(y, "pt"), gp = grid::gpar(col = entry$colour, lineend = "butt",
                                                                   alpha = lines$secondary_opacity + 0.2,
                                                                   lwd = lines$secondary * base * 2 / 0.75)))
  }
  if (entry$kind == "band") {
    side <- swatch_width("square", base, spacing)
    return(grid::rectGrob(grid::unit(entry$x, "pt"), grid::unit(y, "pt"), grid::unit(width, "pt"),
                          grid::unit(side, "pt"), hjust = 0, gp = grid::gpar(fill = entry$colour, col = NA)))
  }
  if (entry$kind == "dash") {
    return(grid::segmentsGrob(grid::unit(entry$x, "pt"), grid::unit(y, "pt"), grid::unit(entry$x + width, "pt"),
                              grid::unit(y, "pt"), gp = grid::gpar(col = entry$colour, lty = "22",
                                                                   lwd = lines$reference * base / 0.75)))
  }
  if (entry$kind %in% c("square", "dot")) {
    return(grid::rectGrob(grid::unit(entry$x, "pt"), grid::unit(y, "pt"), grid::unit(width, "pt"),
                          grid::unit(width, "pt"), hjust = 0, gp = grid::gpar(fill = entry$colour, col = NA)))
  }
  grid::segmentsGrob(grid::unit(entry$x, "pt"), grid::unit(y, "pt"), grid::unit(entry$x + width, "pt"),
                     grid::unit(y, "pt"), gp = grid::gpar(col = entry$colour, lwd = lines$data * base / 0.75,
                                                          lineend = "butt"))
}

# Line tokens with the data and secondary widths of a panel's step.
scaled_lines <- function(scale) {
  lines <- hl_tokens()$lines
  lines$data <- lines$data * scale
  lines$secondary <- lines$secondary * scale
  lines
}

legend_grobs <- function(placed, centers, style, base, height, cap_height, scale = 1) {
  spacing <- hl_tokens()$spacing
  lines <- scaled_lines(scale)
  grobs <- list()
  for (entry in placed) {
    center <- centers[entry$row + 1]
    grobs[[length(grobs) + 1]] <- swatch_grob(entry, center, height, base, spacing, lines)
    text_x <- entry$x + swatch_width(entry$kind, base, spacing) + spacing$legend_swatch_text * base
    grobs[[length(grobs) + 1]] <- text_grob_pt(entry$label, text_x, center + style$size * cap_height / 2, style,
                                               height)
  }
  grobs
}

hairline_legend <- S7::new_class("hairline_legend", package = "hairline", properties = list(items = S7::class_any))

#' Explicit legend items
#'
#' Replaces the legend row collected from the plot's colour and fill scales
#' with these items, e.g. to explain line kinds instead of groups.
#'
#' @param items List of `list(kind, colour, label)`; `kind` is one of `"line"`, `"thin"`, `"dash"`,
#'   `"band"`, `"dot"`, `"square"`.
#' @return An object to add to a ggplot with `+`.
#' @export
hl_legend <- function(items) {
  kinds <- c("line", "thin", "dash", "band", "dot", "square")
  for (item in items) {
    if (!item$kind %in% kinds) {
      stop(sprintf("hairline: unknown legend kind '%s' for '%s'; use one of %s", item$kind, item$label,
                   paste(kinds, collapse = ", ")), call. = FALSE)
    }
  }
  hairline_legend(items = items)
}

add_hairline_legend <- function(object, plot, ...) {
  if (!S7::S7_inherits(plot, hairline_plot)) plot <- hairline_plot(plot)
  plot@meta$hairline_legend <- object@items
  plot
}

reference_legend_items <- function(built) {
  items <- list()
  for (reference in built@plot@meta$hairline_references %||% list()) {
    if (is.null(reference$legend_label)) next
    items[[length(items) + 1]] <- list(kind = "dash", colour = hl_tokens()$reference$color,
                                       label = reference$legend_label)
  }
  items
}
