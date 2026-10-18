# Interactive tags for drawn shapes, mirroring the Python tips module: the series a shape belongs to, its tooltip, and
# where the tooltip points (the middle point of a line, the centroid of a polygon).

tagged_shape <- function(shape, series, tip) {
  points <- shape_points(shape)
  anchor <- if (shape$kind == "line") points[nrow(points) %/% 2 + 1, ] else colMeans(points)
  c(shape, list(series = series, tip = tip, tip_at = unname(anchor)))
}

# An amount with the shared digits rule (whole numbers whole).
amount_text <- function(value) hl_format_number(value, auto_digits(value))
