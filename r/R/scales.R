#' Colour and fill scales from hairline palettes and ramps
#'
#' Discrete scales give every level its entity colour (see [hl_color()]) when
#' `palette` is `NULL`, or the palette's slots in order otherwise, and refuse
#' more categories than slots; continuous scales use a sequential or diverging ramp.
#' Charts made with hairline's own functions pick their colours already; these
#' scales are for plots built with ggplot2 directly.
#'
#' @param palette Palette or purpose-set name (see [hl_palettes()]), hex vector, or `NULL` for the active
#'   palette with entity colours.
#' @param ramp Ramp name for continuous scales: `"blues"`, `"teals"`, `"oranges"`, `"berries"`, `"greys"`, or a
#'   diverging `"blue-coral"` or `"teal-berry"` for values on both sides of a midpoint.
#' @param ... Passed to the underlying ggplot2 scale.
#' @return A ggplot2 scale.
#' @examples
#' ggplot2::ggplot(datasets::iris, ggplot2::aes(Sepal.Length, Petal.Length, colour = Species)) +
#'   ggplot2::geom_point() + ggplot2::labs(title = "Petal by sepal length") + theme_hairline() +
#'   scale_colour_hairline()
#' ggplot2::ggplot(ggplot2::faithfuld, ggplot2::aes(waiting, eruptions, fill = density)) +
#'   ggplot2::geom_raster() + ggplot2::labs(title = "Old Faithful eruptions") + theme_hairline() +
#'   scale_fill_hairline_c("teals")
#' @seealso [hl_palettes()], [hl_swatches()].
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
