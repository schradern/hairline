#' Colour and fill scales from hairline palettes and ramps
#'
#' Discrete scales give every level its entity colour (see [hl_color()]) when
#' `palette` is `NULL`, or the palette's slots in order otherwise, and refuse
#' more categories than slots; continuous scales use a sequential or diverging ramp.
#'
#' @param palette Palette name, hex vector, or `NULL` for the active palette.
#' @param ramp Ramp name for continuous scales.
#' @param ... Passed to the underlying ggplot2 scale.
#' @return A ggplot2 scale.
#' @export
scale_colour_hairline <- function(palette = NULL, ...) {
  scale <- ggplot2::discrete_scale(aesthetics = "colour", palette = function(n) hl_palette(palette, n = n), ...)
  scale$hairline_entity <- is.null(palette)
  scale
}

#' @rdname scale_colour_hairline
#' @export
scale_fill_hairline <- function(palette = NULL, ...) {
  scale <- ggplot2::discrete_scale(aesthetics = "fill", palette = function(n) hl_palette(palette, n = n), ...)
  scale$hairline_entity <- is.null(palette)
  scale
}

#' @rdname scale_colour_hairline
#' @export
scale_colour_hairline_c <- function(ramp = "blues", ...) ggplot2::scale_colour_gradientn(colours = hl_ramp(ramp), ...)

#' @rdname scale_colour_hairline
#' @export
scale_fill_hairline_c <- function(ramp = "blues", ...) ggplot2::scale_fill_gradientn(colours = hl_ramp(ramp), ...)
