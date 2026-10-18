# Donut geometry in pt, the same algorithm as the Python package's donut_geometry: segment outlines with
# constant-width gaps, outside labels with leader lines, labels along the rings, centre total, hierarchical key.

degrees <- function(radians) radians * 180 / pi

donut_point <- function(cx, cy, radius, angle) {
  c(cx + radius * cos(angle * pi / 180), cy - radius * sin(angle * pi / 180))
}

donut_arc <- function(cx, cy, radius, start, end, step) {
  count <- max(2, ceiling(abs(start - end) / step) + 1)
  angles <- start + (end - start) * (seq_len(count) - 1) / (count - 1)
  cbind(cx + radius * cos(angles * pi / 180), cy - radius * sin(angles * pi / 180))
}

segment_polygon <- function(cx, cy, inner, outer, span, rules) {
  inset_outer <- degrees(asin(min(1, rules$gap_pt / 2 / outer)))
  inset_inner <- degrees(asin(min(1, rules$gap_pt / 2 / inner)))
  if (span[1] - span[2] <= 2 * inset_inner) return(NULL)
  rbind(donut_arc(cx, cy, outer, span[1] - inset_outer, span[2] + inset_outer, rules$arc_step),
        donut_arc(cx, cy, inner, span[2] + inset_inner, span[1] - inset_inner, rules$arc_step))
}

ring_radii <- function(count, radius, hole, gap) {
  start <- hole * radius
  thickness <- (radius - start - gap * (count - 1)) / count
  lapply(seq_len(count) - 1, function(ring) {
    c(start + ring * (thickness + gap), start + ring * (thickness + gap) + thickness)
  })
}

ring_spans <- function(ring) {
  shares <- vapply(ring, `[[`, numeric(1), "share")
  before <- c(0, cumsum(shares))[seq_along(shares)]
  lapply(seq_along(shares), function(index) c(90 - 360 * before[index], 90 - 360 * (before[index] + shares[index])))
}

segment_shapes <- function(rings, cx, cy, radii, rules) {
  shapes <- list()
  for (ring_index in seq_along(rings)) {
    ring <- rings[[ring_index]]
    spans <- ring_spans(ring)
    for (index in seq_along(ring)) {
      points <- segment_polygon(cx, cy, radii[[ring_index]][1], radii[[ring_index]][2], spans[[index]], rules)
      if (is.null(points)) next
      segment <- ring[[index]]
      shapes[[length(shapes) + 1]] <- tagged_shape(list(kind = "polygon", points = points, fill = segment$color),
                                                   segment$name, paste0(segment$name, ": ", segment$share_text))
    }
  }
  shapes
}

shape_text <- function(x, y, content, role, colour, align = "left", weight = NULL) {
  list(kind = "text", x = x, y = y, text = content, role = role, color = colour, align = align, weight = weight)
}

line_height <- function(style, role) style$sizes[[role]] * (1 + style$line_gap)

baseline_for <- function(centre, style, role) centre + style$cap_height * style$sizes[[role]] / 2
