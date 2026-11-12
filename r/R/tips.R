# Interactive tags for drawn shapes, mirroring the Python tips module: the series a shape belongs to, its tooltip, and
# where the tooltip points (the middle point of a line, the centroid of a polygon).

tagged_shape <- function(shape, series, tip) {
  points <- shape_points(shape)
  anchor <- if (shape$kind == "line") points[nrow(points) %/% 2 + 1, ] else colMeans(points)
  c(shape, list(series = series, tip = tip, tip_at = unname(anchor)))
}

# A row's key numbers as its tooltip, as the numbers beside it read: "Unit A: Median 4.2, n 64". As Python's
# pairs_tip().
pairs_tip <- function(name, pairs) {
  paste0(name, ": ", paste(vapply(pairs, paste, character(1), collapse = " "), collapse = ", "))
}

# The measures a group's tooltip lists: the marks drawn, then the numbers written, then its n.
tip_measures <- function(marks, stats) unique(c(marks, stats, "n"))

# A series' tooltip targets on panel `panel` (in reading order) for interactive HTML, in that panel's data, as
# Python's HairlineFigure.target(): `marks` its shapes (list(polygon = matrix, alpha =), list(line = matrix, width =),
# list(rect = c(x0, y0, x1, y1)), list(dot = c(x, y), r =), list(diamond = c(x, y), r =); any of them with color,
# edge and edge_width) and `tips`, each list(at = c(x, y), text =) or list(at = c(x, y), value =, axis = "y").
chart_target <- function(panel, name, colour, marks, tips) {
  list(panel = panel, name = name, colour = colour, marks = marks, tips = tips)
}

# An amount with the shared digits rule (whole numbers whole).
amount_text <- function(value) hl_format_number(value, auto_digits(value))
