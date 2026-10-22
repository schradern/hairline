# Named palettes, purpose sets and ramps from the shared tokens.

purpose_sets <- c("pair", "pair-teal", "pair-print", "ink", "judgement")
colour_kinds <- c("categorical", "purpose", "sequential", "diverging")

# A palette or purpose set by name (judgement in its order: low, some concerns, high); NULL for other names.
named_colours <- function(name) {
  tokens <- hl_tokens()
  if (name %in% names(tokens$palettes)) return(unname(tokens$palettes[[name]]))
  if (name == "judgement") return(unname(unlist(tokens$sets$judgement[c("low", "some", "high")])))
  if (name %in% purpose_sets) unname(unlist(tokens$sets[[name]])) else NULL
}

resolve_palette <- function(name) {
  tokens <- hl_tokens()
  if (is.null(name)) {
    settings <- hl_settings()
    return(list(label = settings$palette_label, colors = settings$palette))
  }
  if (is.character(name) && length(name) == 1 && !startsWith(name, "#")) {
    colors <- named_colours(name)
    if (is.null(colors) && name %in% names(tokens$ramps)) {
      stop(sprintf("hairline: '%s' is a ramp, not a palette; use hl_ramp('%s') or a continuous colour scale",
                   name, name), call. = FALSE)
    }
    if (is.null(colors)) {
      stop(sprintf("hairline: unknown palette '%s'; available palettes: %s", name,
                   paste(c(names(tokens$palettes), purpose_sets), collapse = ", ")), call. = FALSE)
    }
    return(list(label = sprintf("palette '%s'", name), colors = colors))
  }
  for (color in name) parse_hex(color)
  list(label = "custom palette", colors = unname(name))
}

#' Palette colours in slot order
#'
#' Colours for groups, in the order hairline assigns them: two groups take
#' slots 1-2, three groups slots 1-3, and a group keeps its colour when more
#' are shown. There are six categorical palettes of eight slots, each opening
#' blue then red so two groups always read blue against red (`"daylight"`, the
#' default, `"calm"`, `"deep"`, `"lagoon"`, `"citrus"` and `"bold"`), and
#' purpose sets for common cases: `"pair"`, `"pair-teal"` and `"pair-print"`
#' for two groups, `"ink"` for greyscale print and `"judgement"` for low, some
#' concerns and high. [hl_palettes()] lists them all with their uses and
#' [hl_swatches()] draws them; make one the default with `hl_use(palette = )`.
#' For amounts, use a ramp ([hl_ramp()]) instead.
#'
#' @param name Palette or purpose-set name, a vector of hex colours, or `NULL` for the active palette.
#' @param n Number of categories; raises an error rather than repeating colours.
#' @return Character vector of hex colours.
#' @seealso [hl_palettes()], [hl_swatches()], [hl_check_palette()], [hl_use()].
#' @examples
#' hl_palette()
#' hl_palette(n = 3)
#' hl_palette("pair")
#' hl_palette("calm", n = 4)
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
#' Colours for amounts. Sequential ramps run light to dark in one hue
#' (`"blues"`, `"teals"`, `"oranges"`, `"berries"`, `"greys"`); diverging
#' ramps run from one pole through a neutral midpoint to the other
#' (`"blue-coral"`, `"teal-berry"`), for values below and above a reference.
#' [scale_colour_hairline_c()] and [scale_fill_hairline_c()] use them in a plot.
#' While a brand is active, `"brand-sequential"` and `"brand-diverging"` follow
#' its colours (its `sequential` and `diverging` entries, else its first one
#' and two colours) and become the default.
#'
#' @param name Ramp name, e.g. `"blues"` or `"blue-coral"`; `NULL` for the default ramp (the brand's while one is
#'   active, else `"blues"`).
#' @param n Number of colours; other counts than the stored 7 (or 13) interpolate in OKLab.
#' @return Character vector of hex colours.
#' @seealso [hl_palettes()], [hl_swatches()].
#' @examples
#' hl_ramp("blues")
#' hl_ramp("blues", n = 3)
#' hl_ramp("blue-coral", n = 5)
#' @export
hl_ramp <- function(name = NULL, n = NULL) {
  ramps <- active_ramps()
  name <- name %||% default_ramp()
  if (!name %in% names(ramps) && !is.null(named_colours(name))) {
    stop(sprintf("hairline: '%s' is a palette, not a ramp; use hl_palette('%s') for groups", name, name),
         call. = FALSE)
  }
  if (!name %in% names(ramps)) {
    stop(sprintf("hairline: unknown ramp '%s'; available ramps: %s", name, paste(names(ramps), collapse = ", ")),
         call. = FALSE)
  }
  colors <- unname(ramps[[name]])
  if (is.null(n) || n == length(colors)) colors else interpolate_colors(colors, n)
}

# The token ramps, and while a brand is active its own two.
active_ramps <- function() c(lapply(hl_tokens()$ramps, unname), hl_settings()$ramps %||% list())

# The ramp used where none is named: the brand's while one is active, else blues and the heatmap's.
default_ramp <- function(kind = "sequential") {
  brand <- if (kind == "sequential") "brand-sequential" else "brand-diverging"
  if (brand %in% names(active_ramps())) return(brand)
  if (kind == "sequential") "blues" else hl_tokens()$correlation$ramp
}

ramp_kind <- function(name) {
  if (name %in% c(names(hl_tokens()$ramp_definitions$diverging), "brand-diverging")) "diverging" else "sequential"
}

# Colour sets as rows (name, kind, use, colours), grouped by kind in catalogue order.
swatch_rows <- function(names = NULL) {
  tokens <- hl_tokens()
  every <- c(names(tokens$palettes), purpose_sets, names(active_ramps()))
  if (!is.null(names) && !length(names)) {
    stop("hairline: swatches: no colour sets named; pass NULL for all of them, or names from hl_palettes()",
         call. = FALSE)
  }
  unknown <- setdiff(names, every)
  if (length(unknown) > 0) {
    stop(sprintf("hairline: unknown colour set '%s'; use one of %s", unknown[1], paste(every, collapse = ", ")),
         call. = FALSE)
  }
  chosen <- if (is.null(names)) every else every[every %in% names]
  rows <- lapply(chosen, function(name) {
    kind <- if (name %in% names(tokens$palettes)) "categorical" else if (name %in% purpose_sets) "purpose" else
      ramp_kind(name)
    colours <- if (kind %in% c("categorical", "purpose")) named_colours(name) else hl_ramp(name)
    list(name = name, kind = kind, use = tokens$colour_notes[[name]], colors = colours)
  })
  rows[order(match(vapply(rows, `[[`, character(1), "kind"), colour_kinds))]
}

#' Every colour set, with its use
#'
#' The catalogue of hairline's colours: categorical palettes and purpose sets
#' for groups, sequential and diverging ramps for amounts. `active` marks the
#' palette in use; a palette from a brand or `hl_use(palette = c(...))` comes
#' first. Use a name with [hl_palette()], `hl_use(palette = )` or [hl_ramp()].
#'
#' @param kind `NULL` for all, or one of `"categorical"`, `"purpose"`, `"sequential"`, `"diverging"`.
#' @return A data frame with `name`, `kind`, `slots`, `active`, `use` and `colors` (hex codes separated by spaces).
#' @seealso [hl_swatches()] draws them.
#' @examples
#' hl_palettes()
#' hl_palettes("purpose")
#' @export
hl_palettes <- function(kind = NULL) {
  if (!is.null(kind) && !kind %in% colour_kinds) {
    stop(sprintf("hairline: unknown kind '%s'; use one of %s", kind, paste(colour_kinds, collapse = ", ")),
         call. = FALSE)
  }
  settings <- hl_settings()
  rows <- swatch_rows()
  is_active <- function(row) row$kind %in% c("categorical", "purpose") && identical(row$name, settings$palette_name)
  table <- data.frame(name = vapply(rows, `[[`, character(1), "name"),
                      kind = vapply(rows, `[[`, character(1), "kind"),
                      slots = vapply(rows, function(row) length(row$colors), integer(1)),
                      active = vapply(rows, is_active, logical(1)),
                      use = vapply(rows, `[[`, character(1), "use"),
                      colors = vapply(rows, function(row) paste(row$colors, collapse = " "), character(1)))
  if (is.null(named_colours(settings$palette_name))) {
    custom <- data.frame(name = settings$palette_name, kind = "categorical", slots = length(settings$palette),
                         active = TRUE, use = paste("the active", settings$palette_label),
                         colors = paste(settings$palette, collapse = " "))
    table <- rbind(custom, table)
  }
  if (!is.null(kind)) table <- table[table$kind == kind, , drop = FALSE]
  rownames(table) <- NULL
  table
}
