# Entity colours: one colour per entity for the whole session.

assign_colors <- function(palette, label, fixed, requests) {
  mapping <- fixed
  taken <- unname(fixed)
  for (name in requests) {
    if (name %in% names(mapping)) next
    free <- setdiff(palette, taken)
    if (length(free) == 0) {
      needed <- unique(c(names(mapping), requests))
      stop(sprintf(paste0("hairline: %s has %d slots but %d categories need colours: %s; ",
                          "fold small categories into 'Other' or split the figure into panels"),
                   label, length(palette), length(needed), paste(needed, collapse = ", ")), call. = FALSE)
    }
    mapping[[name]] <- free[1]
    taken <- c(taken, free[1])
  }
  unlist(mapping[requests])
}

configure_entities <- function(fixed) {
  hairline_state$entities <- list(fixed = fixed %||% character(), auto = character())
}

entity_state <- function() hairline_state$entities %||% list(fixed = character(), auto = character())

#' Entity colours
#'
#' `hl_color()` returns an entity's colour, assigning the first free palette
#' slot the first time an entity is seen; the colour stays for the session.
#' `hl_colors()` returns every colour fixed or assigned so far.
#'
#' @param name Entity name, e.g. a ward or treatment arm.
#' @return A hex colour, or a named character vector.
#' @export
hl_color <- function(name) {
  state <- entity_state()
  known <- c(state$fixed, state$auto)
  if (name %in% names(known)) return(unname(known[[name]]))
  settings <- hl_settings()
  colour <- assign_colors(settings$palette, settings$palette_label, as.list(known), name)
  state$auto <- c(state$auto, colour)
  hairline_state$entities <- state
  unname(colour)
}

#' @rdname hl_color
#' @export
hl_colors <- function() {
  state <- entity_state()
  c(state$fixed, state$auto)
}

validated_entity_colors <- function(colors) {
  for (name in names(colors)) {
    tryCatch(parse_hex(colors[[name]]), error = function(error) {
      stop(sprintf("hairline: colors['%s']: %s", name, conditionMessage(error)), call. = FALSE)
    })
  }
  if (length(colors)) stats::setNames(tolower(unname(colors)), names(colors)) else character()
}

entity_scales <- function(plot, built) {
  scales <- list()
  for (aesthetic in c("colour", "fill")) {
    scale <- built@plot@scales$get_scales(aesthetic)
    user_scale <- plot@scales$has_scale(aesthetic) && !isTRUE(scale$hairline_entity)
    if (is.null(scale) || user_scale || !scale$is_discrete() || isTRUE(scale$hairline_resolved)) next
    levels <- scale$get_limits()
    if (length(levels) == 0) next
    values <- vapply(levels, hl_color, character(1))
    replacement <- ggplot2::scale_colour_manual(values = values, aesthetics = aesthetic)
    replacement$hairline_entity <- TRUE
    replacement$hairline_resolved <- TRUE
    scales[[length(scales) + 1]] <- replacement
  }
  scales
}
