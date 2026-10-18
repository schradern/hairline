# Swatch chart, mirroring the Python swatches(): colour sets grouped under headings, each a name and its use beside a
# row of squares, sized to fit the width.

swatch_ramp_kinds <- c("sequential", "diverging")

# The largest square up to the token size that fits the longest row; too narrow a figure is an error.
swatch_size <- function(rows, left, right, rules, base) {
  slots <- max(vapply(rows, function(row) length(row$colors), integer(1)))
  size <- min(rules$swatch * base, (right - left - (slots - 1) * rules$gap_pt) / slots)
  if (size < rules$min_swatch * base) {
    stop(sprintf(paste0("hairline: swatches: the figure is too narrow for %d colours in a row; use a wider size ",
                        "or fewer sets"), slots), call. = FALSE)
  }
  size
}

# One tagged square per colour; near-white colours get an outline so they stay visible.
swatch_squares <- function(row, left, top, size, rules, style) {
  step <- if (row$kind %in% swatch_ramp_kinds) "step " else ""
  lapply(seq_along(row$colors), function(index) {
    colour <- row$colors[[index]]
    x <- left + (index - 1) * (size + rules$gap_pt)
    square <- list(kind = "polygon", role = "swatch", fill = colour,
                   points = rbind(c(x, top), c(x + size, top), c(x + size, top + size), c(x, top + size)))
    if (contrast_ratio(colour, style$neutral$surface) < rules$edge_contrast) {
      square$edge <- style$neutral$axis
      square$edge_width <- style$leader_width
    }
    tagged_shape(square, row$name, sprintf("%s %s%d: %s", row$name, step, index, colour))
  })
}

swatches_drawing <- function(spec, box, measure, style) {
  rules <- hl_tokens()$swatches
  base <- style$base
  rows <- spec$rows
  labels <- max(vapply(rows, function(row) max(measure(row$name, "label"), measure(row$use, "label")), numeric(1)))
  left <- box[1] + labels + rules$column_gap * base
  size <- swatch_size(rows, left, box[1] + box[3], rules, base)
  label_line <- line_height(style, "label")
  heading_line <- line_height(style, "panel")
  block <- max(size, 2 * label_line)
  shapes <- list()
  y <- box[2]
  kind <- NULL
  for (row in rows) {
    if (!identical(row$kind, kind)) {
      if (!is.null(kind)) y <- y + rules$group_gap * base
      shapes[[length(shapes) + 1]] <- shape_text(box[1], baseline_for(y + heading_line / 2, style, "panel"),
                                                 rules$headings[[row$kind]], "panel", style$neutral$ink)
      y <- y + heading_line + rules$heading_gap * base
      kind <- row$kind
    }
    shapes[[length(shapes) + 1]] <- shape_text(box[1], baseline_for(y + label_line / 2, style, "label"), row$name,
                                               "label", style$neutral$ink)
    shapes[[length(shapes) + 1]] <- shape_text(box[1], baseline_for(y + label_line * 1.5, style, "label"), row$use,
                                               "label", style$neutral$muted)
    shapes <- c(shapes, swatch_squares(row, left, y + (block - size) / 2, size, rules, style))
    y <- y + block + rules$row_gap * base
  }
  shapes
}

#' Colour sets as swatches
#'
#' Draws palettes, purpose sets and ramps as rows of squares under their
#' headings, each with its use, to choose colours by eye. In HTML output each
#' square shows its slot and hex code on hover.
#'
#' @param names Colour sets to show, as [hl_palettes()] lists them; `NULL` shows all, in catalogue order.
#' @param title,subtitle,caption Frame texts; the title defaults to "Colour sets".
#' @return A ggplot with the hairline frame.
#' @seealso [hl_palettes()], [hl_palette()], [hl_ramp()].
#' @examples
#' hl_swatches()
#' hl_swatches(c("daylight", "calm", "pair", "blues"), title = "Colours for this report")
#' @export
hl_swatches <- function(names = NULL, title = NULL, subtitle = NULL, caption = NULL) {
  rows <- swatch_rows(names)
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title %||% "Colour sets", subtitle = subtitle, caption = caption, x = NULL, y = NULL) +
    theme_hairline(axes = FALSE)
  plot@meta$hairline_drawing <- function(box, measure, style) swatches_drawing(list(rows = rows), box, measure, style)
  plot@meta$hairline_fit_height <- TRUE
  plot
}
