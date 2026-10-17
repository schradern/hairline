#' @keywords internal
"_PACKAGE"

hairline_state <- new.env(parent = emptyenv())

#' Shared design tokens
#'
#' Returns the design tokens shared by the R and Python packages (type and
#' spacing scales, line widths, neutral colours, palettes, size presets).
#'
#' @return A named list.
#' @keywords internal
hl_tokens <- function() {
  if (is.null(hairline_state$tokens)) {
    path <- system.file("tokens", "hairline.json", package = "hairline")
    if (!nzchar(path)) {
      stop("hairline: bundled tokens missing in inst/tokens/hairline.json; reinstall the package", call. = FALSE)
    }
    hairline_state$tokens <- jsonlite::read_json(path, simplifyVector = TRUE)
  }
  hairline_state$tokens
}
