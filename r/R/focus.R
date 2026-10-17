# Guiding focus: highlight series or panels, reference lines with labels.

hairline_highlight <- S7::new_class("hairline_highlight", package = "hairline",
                                    properties = list(series = S7::class_any, panels = S7::class_any))

hairline_reference <- S7::new_class("hairline_reference", package = "hairline",
                                    properties = list(y = S7::class_any, x = S7::class_any, label = S7::class_any,
                                                      legend_label = S7::class_any))

#' Highlight series or panels
#'
#' Keeps the named series (legend labels of the colour or fill mapping) or
#' panels (facet label or 1-based index) in their colours and draws every other
#' data series in the context grey.
#'
#' @param series Legend labels to keep in colour.
#' @param panels Facet labels or 1-based panel numbers to keep in colour.
#' @return An object to add to a ggplot with `+`.
#' @export
hl_highlight <- function(series = NULL, panels = NULL) hairline_highlight(series = series, panels = panels)

#' Reference line with a label
#'
#' A thin dashed line (threshold, target) behind the data in every panel, with
#' an optional label at its end and an optional legend entry.
#'
#' @param y,x Position of a horizontal (`y`) or vertical (`x`) line; give exactly one.
#' @param label Text at the end of the line, e.g. `"90 %"`.
#' @param legend_label Text for a dashed legend entry.
#' @return An object to add to a ggplot with `+`.
#' @export
hl_reference <- function(y = NULL, x = NULL, label = NULL, legend_label = NULL) {
  if (is.null(y) == is.null(x)) stop("hairline: hl_reference() needs exactly one of y = or x =", call. = FALSE)
  hairline_reference(y = y, x = x, label = label, legend_label = legend_label)
}

add_hairline_highlight <- function(object, plot, ...) {
  if (!S7::S7_inherits(plot, hairline_plot)) plot <- hairline_plot(plot)
  plot@meta$hairline_highlight <- list(series = object@series, panels = object@panels)
  plot
}

reference_layer <- function(object) {
  rules <- hl_tokens()$reference
  settings <- hl_settings()
  arguments <- list(colour = rules$color, linewidth = pt_to_mm(rules$width * settings$base_size), linetype = "22",
                    inherit.aes = FALSE)
  if (!is.null(object@y)) do.call(ggplot2::geom_hline, c(list(yintercept = object@y), arguments)) else
    do.call(ggplot2::geom_vline, c(list(xintercept = object@x), arguments))
}

add_hairline_reference <- function(object, plot, ...) {
  if (!S7::S7_inherits(plot, hairline_plot)) plot <- hairline_plot(plot)
  plot@layers <- c(list(reference_layer(object)), plot@layers)
  plot@meta$hairline_references <- c(plot@meta$hairline_references %||% list(),
                                     list(list(y = object@y, x = object@x, label = object@label,
                                               legend_label = object@legend_label)))
  plot
}

highlight_colours <- function(built, series) {
  for (scale in built@plot@scales$scales) {
    if (!any(scale$aesthetics %in% c("colour", "fill")) || !scale$is_discrete()) next
    labels <- scale$get_labels(scale$get_breaks())
    unknown <- setdiff(series, labels)
    if (length(unknown)) {
      stop(sprintf("hairline: highlight: '%s' is not a series label; labels: %s", unknown[1],
                   paste(labels, collapse = ", ")), call. = FALSE)
    }
    return(scale$map(scale$get_breaks()[match(series, labels)]))
  }
  stop("hairline: highlight(series =) needs a discrete colour or fill mapping", call. = FALSE)
}

highlight_panels <- function(built, panels) {
  facets <- facet_labels(built)
  labels <- vapply(facets$labels, function(label) label %||% "", character(1))
  ids <- vapply(panels, function(panel) {
    if (is.numeric(panel) && panel >= 1 && panel <= length(labels)) return(as.integer(panel))
    if (panel %in% labels) return(match(panel, labels))
    stop(sprintf("hairline: highlight: panel '%s' does not exist; panel names: %s", panel,
                 paste(labels, collapse = ", ")), call. = FALSE)
  }, integer(1))
  sort(unique(built@layout$layout$PANEL[order(built@layout$layout$ROW, built@layout$layout$COL)][ids]))
}

restyle_layer <- function(data, keep, geom, rules) {
  context <- rules$context
  if ("colour" %in% names(data)) data$colour[!keep] <- context
  if ("fill" %in% names(data) && geom != "GeomPoint") data$fill[!keep] <- context
  if (geom %in% c("GeomLine", "GeomPath", "GeomStep") && "linewidth" %in% names(data)) {
    data$linewidth <- data$linewidth * ifelse(keep, rules$highlight_width, rules$context_width)
  }
  data$.hairline_context <- !keep
  data
}

apply_highlight <- function(built) {
  spec <- built@plot@meta$hairline_highlight
  if (is.null(spec)) return(built)
  rules <- hl_tokens()$focus
  colours <- if (!is.null(spec$series)) highlight_colours(built, spec$series) else NULL
  panels <- if (!is.null(spec$panels)) highlight_panels(built, spec$panels) else NULL
  for (index in seq_along(built@data)) {
    geom <- class(built@plot@layers[[index]]$geom)[1]
    if (geom %in% c("GeomHline", "GeomVline") || isTRUE(built@plot@layers[[index]]$hairline_decoration)) next
    data <- built@data[[index]]
    keep <- rep(TRUE, nrow(data))
    if (!is.null(colours) && "colour" %in% names(data)) keep <- keep & data$colour %in% colours
    if (!is.null(panels)) keep <- keep & as.integer(data$PANEL) %in% as.integer(panels)
    built@data[[index]] <- restyle_layer(data, keep, geom, rules)
  }
  built
}

reference_label_below <- function(y, range, panel_height, label_size, base_size) {
  tokens <- hl_tokens()
  gap <- tokens$reference$label_gap * label_size
  offset <- (range[2] - y) / diff(range) * panel_height
  offset - gap - font_metrics()$cap_height * label_size < -tokens$spacing$panel_header * base_size
}
