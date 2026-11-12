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

# A title at the start of the legend row, naming what the series are ("Risk group"); none for an empty legend.
titled_legend <- function(items, title) {
  if (is.null(title) || !length(items)) return(items)
  c(list(list(kind = "title", colour = NA, label = as.character(title))), items)
}

legend_items <- function(built) {
  items <- list()
  seen <- character()
  for (scale in built@plot@scales$scales) {
    aesthetic <- intersect(scale$aesthetics, c("colour", "fill"))[1]
    # A scale drawn without a guide (one series, nothing to tell apart) has no legend entry.
    if (identical(scale$guide, "none") || inherits(scale$guide, "GuideNone")) next
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
    if (!is.null(highlighted)) colours[!labels %in% highlighted] <- context_colour()
    for (index in seq_along(breaks)) {
      if (is.na(labels[index]) || labels[index] %in% seen) next
      seen <- c(seen, labels[index])
      items[[length(items) + 1]] <- list(kind = kind, colour = colours[index], label = labels[index])
    }
  }
  items
}

# An open marker's outline (the mean's diamond) as a share of the data line width.
open_edge <- 0.6
legend_kinds <- c("line", "thin", "dash", "band", "dot", "square", "diamond", "tick", "bar", "slim")
# Keys of summary marks (summary =): a median tick across the value axis, and the interval bars, thick (IQR) and slim
# (SD, CI).
square_kinds <- c("dot", "square", "diamond", "tick")

swatch_width <- function(kind, base, spacing) {
  # A key's title (the binned colour key of hl_legend_ramp()) is text without a swatch.
  if (identical(kind, "title")) return(0)
  factor <- if (kind %in% square_kinds) spacing$legend_swatch_square else spacing$legend_swatch_line
  factor * base
}

# Swatch, gap and label; a title is its text alone.
legend_item_width <- function(item, style, base, spacing) {
  label <- text_width_pt(item$label, style)
  if (identical(item$kind, "title")) return(label)
  swatch_width(item$kind, base, spacing) + spacing$legend_swatch_text * base + label
}

# Items left to right, a new row when the next would cross `right`. The `key` (a binned colour key) follows the
# items, from the same left edge as every legend, and moves to a new row as a whole when it does not fit beside them.
pack_legend <- function(items, left, right, style, base, spacing, key = list()) {
  row <- 0
  cursor <- left
  placed <- list()
  gap <- spacing$legend_item * base
  for (item in items) {
    width <- legend_item_width(item, style, base, spacing)
    if (cursor > left && cursor + width > right) {
      row <- row + 1
      cursor <- left
    }
    placed[[length(placed) + 1]] <- c(item, list(row = row, x = cursor, right = cursor + width))
    cursor <- cursor + width + gap
  }
  widths <- vapply(key, legend_item_width, numeric(1), style = style, base = base, spacing = spacing)
  key_width <- if (length(widths)) sum(widths) + gap * (length(widths) - 1) else 0
  if (length(widths) && cursor > left && cursor + key_width > right) {
    row <- row + 1
    cursor <- left
  }
  for (index in seq_along(key)) {
    placed[[length(placed) + 1]] <- c(key[[index]], list(row = row, x = cursor, right = cursor + widths[index]))
    cursor <- cursor + widths[index] + gap
  }
  placed
}

# The binned colour key as legend items: its title, then one outlined square per step.
ramp_key_items <- function(key) {
  if (is.null(key)) return(list())
  title <- if (!is.null(key$title)) list(list(kind = "title", colour = NA, label = key$title))
  c(title, lapply(seq_along(key$colors), function(index) {
    list(kind = "square", colour = key$colors[[index]], label = key$labels[[index]], outline = TRUE)
  }))
}

swatch_grob <- function(entry, center, height, base, spacing, lines) {
  width <- swatch_width(entry$kind, base, spacing)
  if (identical(entry$kind, "title")) return(grid::nullGrob())
  y <- height - center
  if (entry$kind == "diamond") {
    half <- width / 2
    return(grid::polygonGrob(grid::unit(entry$x + c(0, half, width, half), "pt"),
                             grid::unit(y + c(0, half, 0, -half), "pt"),
                             gp = grid::gpar(fill = lines$surface, col = entry$colour, linejoin = "mitre",
                                             lwd = lines$data * base * open_edge / 0.75)))
  }
  if (entry$kind == "tick") {
    side <- swatch_width("square", base, spacing)
    return(grid::segmentsGrob(grid::unit(entry$x + side / 2, "pt"), grid::unit(y - side / 2, "pt"),
                              grid::unit(entry$x + side / 2, "pt"), grid::unit(y + side / 2, "pt"),
                              gp = grid::gpar(col = entry$colour, lwd = lines$data * base / 0.75, lineend = "butt")))
  }
  if (entry$kind %in% c("bar", "slim")) {
    rules <- hl_tokens()$summary
    side <- swatch_width("square", base, spacing) * rules$key_bar * if (entry$kind == "slim") rules$thin_bar else 1
    return(grid::rectGrob(grid::unit(entry$x, "pt"), grid::unit(y, "pt"), grid::unit(width, "pt"),
                          grid::unit(side, "pt"), hjust = 0, gp = grid::gpar(fill = entry$colour, col = NA)))
  }
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
    # An outlined square (a binned colour key) keeps its lightest step visible on the surface.
    edge <- if (isTRUE(entry$outline)) hl_tokens()$legend_ramp$outline * base else 0
    return(grid::rectGrob(grid::unit(entry$x, "pt"), grid::unit(y, "pt"), grid::unit(width, "pt"),
                          grid::unit(width, "pt"), hjust = 0,
                          gp = grid::gpar(fill = entry$colour, col = if (edge > 0) lines$outline_colour else NA,
                                          lwd = edge / 0.75, linejoin = "mitre")))
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

legend_grobs <- function(placed, centers, style, base, height, cap_height, scale = 1, outline = NULL,
                         surface = "#ffffff") {
  spacing <- hl_tokens()$spacing
  lines <- scaled_lines(scale)
  lines$outline_colour <- outline
  lines$surface <- surface
  grobs <- list()
  for (entry in placed) {
    center <- centers[entry$row + 1]
    grobs[[length(grobs) + 1]] <- swatch_grob(entry, center, height, base, spacing, lines)
    text_x <- if (identical(entry$kind, "title")) entry$x else
      entry$x + swatch_width(entry$kind, base, spacing) + spacing$legend_swatch_text * base
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
#'   `"band"`, `"dot"`, `"square"`, `"diamond"` (an open marker, such as a mean), `"tick"` (a median across
#'   the value axis), `"bar"` and `"slim"` (interval bars: an IQR, an SD or CI).
#' @return An object to add to a ggplot with `+`.
#' @examples
#' ggplot2::ggplot(datasets::mtcars, ggplot2::aes(wt, mpg)) + ggplot2::geom_point() +
#'   ggplot2::labs(title = "Fuel use by weight") + theme_hairline() +
#'   hl_legend(list(list(kind = "dot", colour = hl_palette(n = 1), label = "Car")))
#' @export
hl_legend <- function(items) {
  kinds <- legend_kinds
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
