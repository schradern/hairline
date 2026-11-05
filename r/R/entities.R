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

chart_colours <- function(palette, label, fixed, remembered, override, names, reserved = character(),
                          dimension = NULL) {
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
    free <- setdiff(setdiff(palette, used), names(reserved))
    if (length(free) == 0) stop(no_room(palette, label, names, reserved, dimension), call. = FALSE)
    result[[name]] <- free[1]
    used <- c(used, free[1])
  }
  result[names]
}

# The palette is full: either this chart's categories alone, or together with the slots another dimension holds
# (then both dimensions are named, so the reader knows which colours to pin or free).
no_room <- function(palette, label, names, reserved, dimension) {
  if (length(reserved) && length(names) <= length(palette)) {
    others <- sort(unique(unname(reserved)))
    return(sprintf(paste0("hairline: %s has %d slots; %d are held by dimension %s and %d categories of dimension ",
                          "'%s' need colours: %s; use fewer categories, pin colours with hl_use(colors = ...) or ",
                          "give the dimensions one palette each"), label, length(palette), length(reserved),
                   paste0("'", others, "'", collapse = ", "), length(names), dimension %||% "None",
                   paste(names, collapse = ", ")))
  }
  sprintf(paste0("hairline: %s has %d slots but %d categories need colours: %s; ",
                 "fold small categories into 'Other' or split the figure into panels"),
          label, length(palette), length(names), paste(names, collapse = ", "))
}

# Colours remembered for names of other dimensions than `dimension` (NULL: names given no dimension), named by
# colour, each holding its dimension.
reserved_colours <- function(dimension) {
  state <- entity_state()
  known <- c(state$fixed, state$auto)
  known <- known[!duplicated(names(known), fromLast = TRUE)]
  owners <- vapply(names(known), function(name) state$dimensions[[name]] %||% "None", character(1))
  other <- owners != (dimension %||% "None")
  stats::setNames(unname(owners[other]), unname(known[other]))
}

# The colours of one chart's groups; names seen for the first time are remembered for later charts, a chart's own
# `colors` are not. `dimension` names what the groups are (procedures, application patterns): groups of one dimension
# keep clear of the slots another dimension holds; without one, the enclosing hl_scope() applies.
colours_for <- function(names, colors = NULL, dimension = NULL) {
  settings <- hl_settings()
  state <- entity_state()
  dimension <- dimension %||% current_dimension()
  override <- if (length(colors)) stats::setNames(tolower(unname(colors)), names(colors)) else character()
  mapping <- chart_colours(settings$palette, settings$palette_label, state$fixed, state$auto, override,
                           as.character(names), reserved_colours(dimension), dimension)
  fresh <- setdiff(names(mapping), c(names(override), names(state$fixed), names(state$auto)))
  if (length(fresh)) {
    state$auto <- c(state$auto, mapping[fresh])
    if (!is.null(dimension)) state$dimensions[fresh] <- dimension
    hairline_state$entities <- state
  }
  mapping
}

#' Colour scopes
#'
#' Charts drawn inside take `dimension` for their groups: their categories keep clear of the palette slots the
#' session has given to another dimension, as `dimension =` on each chart would. A figure of application patterns
#' then never reuses the blue a procedure holds, as long as the palette has room; an error names both dimensions
#' when it has not.
#'
#' @param dimension What the groups are, e.g. `"pattern"`.
#' @param code Code that draws the charts.
#' @return The value of `code`.
#' @examples
#' hl_use(brand = FALSE)
#' procedures <- hl_bars(data.frame(group = c("A", "B"), n = c(3, 4)), "group", "n", by = "group")
#' hl_scope("pattern", hl_bars(data.frame(kind = c("Bolus", "Infusion"), n = c(5, 2)), "kind", "n", by = "kind"))
#' hl_use()
#' @export
hl_scope <- function(dimension, code) {
  hairline_state$dimensions <- c(hairline_state$dimensions, as.character(dimension))
  on.exit(hairline_state$dimensions <- utils::head(hairline_state$dimensions, -1))
  code
}

current_dimension <- function() {
  dimensions <- hairline_state$dimensions
  if (length(dimensions)) dimensions[length(dimensions)] else NULL
}

configure_entities <- function(fixed) {
  hairline_state$entities <- list(fixed = fixed %||% character(), auto = character(), dimensions = list())
}

entity_state <- function() {
  hairline_state$entities %||% list(fixed = character(), auto = character(), dimensions = list())
}

#' Entity colours
#'
#' `hl_color()` returns an entity's colour, assigning the first free palette
#' slot the first time an entity is seen; the colour stays for the session.
#' `hl_colors()` returns every colour fixed or assigned so far.
#'
#' @param name Entity name, e.g. a ward or treatment arm.
#' @return A hex colour, or a named character vector.
#' @examples
#' hl_use(colors = c("Unit A" = "#0a6ddd", "Unit B" = "#e79d01"))
#' hl_color("Unit B")
#' hl_colors()
#' hl_use()
#' @export
hl_color <- function(name) {
  state <- entity_state()
  known <- c(state$fixed, state$auto)
  if (name %in% names(known)) return(unname(known[[name]]))
  settings <- hl_settings()
  dimension <- current_dimension()
  reserved <- reserved_colours(dimension)
  free <- setdiff(settings$palette, names(reserved))
  if (length(free) < length(settings$palette) && !length(setdiff(free, unname(known)))) {
    stop(no_room(settings$palette, settings$palette_label, name, reserved, dimension), call. = FALSE)
  }
  colour <- assign_colors(free, settings$palette_label, as.list(known), name)
  state$auto <- c(state$auto, colour)
  if (!is.null(dimension)) state$dimensions[[name]] <- dimension
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
