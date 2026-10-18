# Entity colours: per chart, groups take the colour set for their count; a name keeps its
# colour across charts unless that would clash within one chart. The same rules as the Python package's entities.

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

chart_colours <- function(palette, label, fixed, remembered, override, names) {
  names <- unique(names)
  result <- character()
  for (name in names) {
    if (name %in% names(override)) result[[name]] <- override[[name]] else
      if (name %in% names(fixed)) result[[name]] <- fixed[[name]]
  }
  used <- unname(result)
  for (name in setdiff(names, names(result))) {
    colour <- if (name %in% names(remembered)) remembered[[name]] else NA_character_
    if (!is.na(colour) && !colour %in% used) {
      result[[name]] <- colour
      used <- c(used, colour)
    }
  }
  for (name in setdiff(names, names(result))) {
    free <- setdiff(palette, used)
    if (length(free) == 0) {
      stop(sprintf(paste0("hairline: %s has %d slots but %d categories need colours: %s; ",
                          "fold small categories into 'Other' or split the figure into panels"),
                   label, length(palette), length(names), paste(names, collapse = ", ")), call. = FALSE)
    }
    result[[name]] <- free[1]
    used <- c(used, free[1])
  }
  result[names]
}

# The colours of one chart's groups; names seen for the first time are remembered for later charts, a chart's own
# `colors` are not.
colours_for <- function(names, colors = NULL) {
  settings <- hl_settings()
  state <- entity_state()
  override <- if (length(colors)) stats::setNames(tolower(unname(colors)), names(colors)) else character()
  mapping <- chart_colours(settings$palette, settings$palette_label, state$fixed, state$auto, override,
                           as.character(names))
  fresh <- setdiff(names(mapping), c(names(override), names(state$fixed), names(state$auto)))
  if (length(fresh)) {
    state$auto <- c(state$auto, mapping[fresh])
    hairline_state$entities <- state
  }
  mapping
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
    values <- colours_for(levels)
    replacement <- ggplot2::scale_colour_manual(values = values, aesthetics = aesthetic)
    replacement$hairline_entity <- TRUE
    replacement$hairline_resolved <- TRUE
    scales[[length(scales) + 1]] <- replacement
  }
  scales
}
