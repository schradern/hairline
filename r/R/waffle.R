# Waffle chart: shares of a whole as a square grid of cells (10 x 10, one cell per percent), filled row by row from
# the top left in the slices' order, with a key of names and shares beside it; the same algorithm as the Python
# package's charts/waffle.py.

# Cells per slice by the largest remainder, so they always add up to `cells`; equal remainders go to the earlier
# slice. A slice under half a cell may get none. As Python's cell_counts().
waffle_cell_counts <- function(shares, cells) {
  exact <- shares * cells
  counts <- floor(round(exact, alt_tie_digits))
  remainders <- round(exact - counts, alt_tie_digits)
  ranked <- order(-remainders, seq_along(shares))
  extra <- cells - sum(counts)
  if (extra > 0) counts[ranked[seq_len(extra)]] <- counts[ranked[seq_len(extra)]] + 1
  counts
}

# One square per cell, row by row from the top left; each names its slice and share for the HTML tooltips.
waffle_cells <- function(ring, left, top, side, rules) {
  per_row <- rules$side
  gap <- rules$gap_pt
  cell <- (side - (per_row - 1) * gap) / per_row
  counts <- waffle_cell_counts(vapply(ring, `[[`, numeric(1), "share"), per_row^2)
  fills <- ring[rep(seq_along(ring), counts)]
  lapply(seq_along(fills) - 1, function(index) {
    segment <- fills[[index + 1]]
    tagged_shape(key_square(left + (index %% per_row) * (cell + gap), top + (index %/% per_row) * (cell + gap), cell,
                            segment$color), segment$name, paste0(segment$name, ": ", segment$share_text))
  })
}

# A share of the panel width, smaller where the key needs the room for its names on one line, but never under
# `min_grid_share`: below that the key wraps its names instead. As Python's grid_side().
waffle_grid_side <- function(ring, width, measure, style, rules, key_rules) {
  key_width <- key_right(key_rows(list(ring)), 0, Inf, measure, style, key_rules)
  room <- width - key_rules$key_gap * style$base - key_width
  max(width * rules$min_grid_share, min(width * rules$grid_share, room))
}

# The grid at the panel's top left and the key centred beside it.
waffle_drawing <- function(spec, box, measure, style) {
  rules <- hl_tokens()$waffle
  key_rules <- hl_tokens()$donut
  side <- waffle_grid_side(spec$ring, box[3], measure, style, rules, key_rules)
  key_left <- box[1] + side + key_rules$key_gap * style$base
  c(waffle_cells(spec$ring, box[1], box[2], side, rules),
    hierarchical_key(list(spec$ring), key_left, box, box[2] + side / 2, measure, style, key_rules, "waffle"))
}

#' Waffle chart
#'
#' Shares of a whole as 100 cells, one per percent, filled row by row from the
#' top left, with each slice's name and share in a key beside the grid. More
#' than seven slices fold into "Other", as on the donut. Cells round by the
#' largest remainder, so they add up to 100 and a slice may take one cell more
#' or less than its share in the key.
#'
#' @param data A data frame.
#' @param label Column naming the slices.
#' @param value Column with the amounts; `NULL` counts rows.
#' @param title,subtitle,caption Frame texts.
#' @param colors Named colours for this chart only, e.g. `c(Male = "#0a6ddd")`; they override the colour set
#'   for the number of groups and are not remembered for other charts.
#'   A ramp name such as `"blues"` colours ordered groups light to dark, in the chart's order.
#' @param order Slices in this order; any others follow in their data order.
#' @return A ggplot with the hairline frame.
#' @examples
#' discharge <- data.frame(route = c("Home", "Rehabilitation", "Ward", "Died"),
#'                         patients = c(412, 168, 97, 23))
#' hl_waffle(discharge, "route", "patients")
#' @export
hl_waffle <- function(data, label, value = NULL, title = NULL, subtitle = NULL, caption = NULL, colors = NULL,
                      order = NULL) {
  counted <- with_counts(data, value)
  data <- counted$data
  value <- counted$value
  ring <- donut_rings(data, label, value, NULL, chart = "waffle", colors = colors, order = order)[[1]]
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title %||% paste(humanise(value), "by", joined(label)), subtitle = subtitle,
                  caption = caption, x = NULL, y = NULL) +
    theme_hairline(axes = FALSE)
  plot@meta$hairline_drawing <- function(box, measure, style) waffle_drawing(list(ring = ring), box, measure, style)
  plot@meta$hairline_fit_height <- TRUE
  plot@meta$hairline_description <- donut_description(ring, NULL, NULL, "kind_waffle")
  plot
}
