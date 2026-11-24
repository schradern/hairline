# The tiles of hl_profile(): a histogram per number, bars of shares per category, counts per period per date column,
# each stacked by group when the profile has groups; one ggplot per tile, set in a grid by plot_grid(). As the
# Python package's study/profile_tiles.py.

profile_periods <- c(M = "month", Q = "quarter", Y = "year")

# The header's qualifier: what the tile counts in (`before`), then '9 missing' when values are; it sits beside the
# name, where it is never dropped for room.
profile_missing_note <- function(values, before = NULL) {
  missing <- sum(study_is_missing(values))
  parts <- c(before, if (missing) paste(hl_format_number(missing, 0), "missing"))
  if (length(parts)) paste(parts, collapse = ", ")
}

profile_in_group <- function(stratum) if (is.null(stratum$name)) "" else paste0(", ", stratum$name)

# A bin as a reader names it: '4' for a bin one whole number wide, else '60 to under 65'.
profile_bin_text <- function(left, width, whole, digits) {
  if (whole && width == 1) return(hl_format_number(left + 0.5, 0))
  places <- if (whole) 0 else digits
  paste(hl_format_number(left, places), "to under", hl_format_number(left + width, places))
}

# The colour laid over the surface at the profile's opacity, as one opaque colour: the bars and their legend swatches
# read the same.
profile_fill <- function(colour, surface) {
  opacity <- hl_tokens()$profile$fill_opacity
  mixed <- opacity * grDevices::col2rgb(colour) + (1 - opacity) * grDevices::col2rgb(surface)
  tolower(grDevices::rgb(mixed[1], mixed[2], mixed[3], maxColorValue = 255))
}

# Each stratum's values stacked on the ones before it as rectangles (`spots` are the low and high ends along the
# category axis), with a tooltip target per non-empty segment; the rectangles stay out of the automatic targets.
profile_stack <- function(parts, colours, spots, horizontal, series, tip) {
  base <- rep(0, nrow(spots))
  rects <- list()
  targets <- list()
  for (part in parts) {
    name <- part$stratum$name %||% ".all"
    top <- base + part$values
    rows <- if (horizontal) data.frame(xmin = base, xmax = top, ymin = spots$low, ymax = spots$high) else
      data.frame(xmin = spots$low, xmax = spots$high, ymin = base, ymax = top)
    rects[[length(rects) + 1]] <- cbind(rows, fill = colours[[name]])[part$values > 0, , drop = FALSE]
    for (spot in which(part$values > 0)) {
      middle <- (spots$low[spot] + spots$high[spot]) / 2
      rect <- if (horizontal) c(base[spot], spots$low[spot], top[spot], spots$high[spot]) else
        c(spots$low[spot], base[spot], spots$high[spot], top[spot])
      at <- if (horizontal) c(top[spot], middle) else c(middle, top[spot])
      targets[[length(targets) + 1]] <- chart_target(1, part$stratum$name %||% series, colours[[name]],
                                                     list(list(rect = rect)),
                                                     list(list(at = at, text = tip(spot, part$stratum,
                                                                                   part$values[spot]))))
    }
    base <- top
  }
  list(rects = do.call(rbind, rects), totals = base, targets = targets)
}

profile_rect_layer <- function(rects, settings) {
  static_layer(ggplot2::geom_rect(ggplot2::aes(xmin = .data$xmin, xmax = .data$xmax, ymin = .data$ymin,
                                               ymax = .data$ymax), data = rects, fill = rects$fill,
                                  colour = settings$neutral$surface, inherit.aes = FALSE,
                                  linewidth = pt_to_linewidth(hl_tokens()$bars$gap_pt / 2)))
}

# A tile's ggplot: no titles of its own, its header, the legend row (on the first tile) and its targets.
profile_tile <- function(layers, header, legend, targets) {
  plot <- ggplot2::ggplot() + layers + ggplot2::labs(x = NULL, y = NULL) + theme_hairline() + header + legend
  plot@meta$hairline_targets <- targets
  plot
}

# Counts from zero to a little above the tallest bar, so its top never touches the panel's edge.
profile_count_reach <- function(totals) {
  top <- max(c(totals, 1)) * (1 + hl_tokens()$profile$count_headroom)
  ggplot2::geom_blank(ggplot2::aes(y = .data$y), data = data.frame(y = c(0, top)), inherit.aes = FALSE)
}
