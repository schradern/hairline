# Named palettes, purpose sets and ramps from the shared tokens.

resolve_palette <- function(name) {
  tokens <- hl_tokens()
  if (is.null(name)) {
    settings <- hl_settings()
    return(list(label = settings$palette_label, colors = settings$palette))
  }
  if (is.character(name) && length(name) == 1 && !startsWith(name, "#")) {
    if (!name %in% names(tokens$palettes)) {
      stop(sprintf("hairline: unknown palette '%s'; available palettes: %s", name,
                   paste(names(tokens$palettes), collapse = ", ")), call. = FALSE)
    }
    return(list(label = sprintf("palette '%s'", name), colors = unname(tokens$palettes[[name]])))
  }
  for (color in name) parse_hex(color)
  list(label = "custom palette", colors = unname(name))
}

#' Palette colours in slot order
#'
#' @param name Palette name, a vector of hex colours, or `NULL` for the active palette.
#' @param n Number of categories; raises an error rather than repeating colours.
#' @return Character vector of hex colours.
#' @examples
#' hl_palette()
#' hl_palette(n = 3)
#' @export
hl_palette <- function(name = NULL, n = NULL) {
  resolved <- resolve_palette(name)
  if (is.null(n)) return(resolved$colors)
  if (n > length(resolved$colors)) {
    stop(sprintf(paste0("hairline: %s has %d slots but %d categories were given; ",
                        "fold small categories into 'Other' or split the figure into panels"),
                 resolved$label, length(resolved$colors), n), call. = FALSE)
  }
  resolved$colors[seq_len(n)]
}

interpolate_colors <- function(colors, count) {
  points <- lapply(colors, hex_to_oklab)
  vapply(seq_len(count) - 1, function(index) {
    position <- index * (length(points) - 1) / max(count - 1, 1)
    low <- min(floor(position), length(points) - 2)
    weight <- position - low
    linear_to_hex(oklab_to_linear(points[[low + 1]] + (points[[low + 2]] - points[[low + 1]]) * weight))
  }, character(1))
}

#' Sequential or diverging ramp
#'
#' @param name Ramp name, e.g. `"blues"` or `"blue-coral"`.
#' @param n Number of colours; other counts than the stored 7 (or 13) interpolate in OKLab.
#' @return Character vector of hex colours.
#' @examples
#' hl_ramp("blues")
#' hl_ramp("blues", n = 3)
#' @export
hl_ramp <- function(name, n = NULL) {
  ramps <- hl_tokens()$ramps
  if (!name %in% names(ramps)) {
    stop(sprintf("hairline: unknown ramp '%s'; available ramps: %s", name, paste(names(ramps), collapse = ", ")),
         call. = FALSE)
  }
  colors <- unname(ramps[[name]])
  if (is.null(n) || n == length(colors)) colors else interpolate_colors(colors, n)
}
