# Donut hierarchical key, labels along the rings, and the entry point donut_drawing().

same_index <- function(first, second) {
  if (is.null(first) || is.null(second)) return(is.null(first) && is.null(second))
  first == second
}

key_rows <- function(rings) {
  children <- function(depth, parent) {
    if (depth > length(rings)) return(list())
    rows <- list()
    for (segment in rings[[depth]]) {
      if (!same_index(segment$parent, parent)) next
      rows <- c(rows, list(list(depth = depth - 1, segment = segment)), children(depth + 1, segment$index))
    }
    Filter(function(row) !repeats_parent(row, rows), rows)
  }
  children(1, NULL)
}

repeats_parent <- function(row, rows) {
  parents <- Filter(function(item) item$depth == row$depth - 1 && same_index(item$segment$index, row$segment$parent),
                    rows)
  length(parents) > 0 && parents[[1]]$segment$name == row$segment$name &&
    parents[[1]]$segment$share == row$segment$share
}

key_right <- function(rows, x, right, measure, style, rules) {
  base <- style$base
  names <- max(vapply(rows, function(row) row$depth * rules$key_indent * base + measure(row$segment$name, "label"),
                      numeric(1)))
  shares <- max(vapply(rows, function(row) measure(row$segment$share_text, "label"), numeric(1)))
  min(right, x + (style$swatch + style$swatch_text + rules$key_gap) * base + names + shares)
}

# Each key name's lines: one while names and shares fit the panel, wrapped before the share column otherwise.
key_lines <- function(rows, x, right, measure, style, rules) {
  base <- style$base
  shares <- max(vapply(rows, function(row) measure(row$segment$share_text, "label"), numeric(1)))
  text_left <- (style$swatch + style$swatch_text) * base
  lapply(rows, function(row) {
    fit_lines(row$segment$name, right - shares - rules$key_gap * base - x - row$depth * rules$key_indent * base -
                text_left, measure, "donut", "the key name")
  })
}

key_square <- function(x, y, side, fill) {
  list(kind = "polygon", points = rbind(c(x, y), c(x + side, y), c(x + side, y + side), c(x, y + side)), fill = fill)
}

# Rows centred beside the donut; a name wraps before the share column, which stays on its first line. Rows taller
# than the panel start at its top and run on below it (the figure grows to hold them).
hierarchical_key <- function(rings, x, box, cy, measure, style, rules) {
  base <- style$base
  rows <- key_rows(rings)
  right <- key_right(rows, x, box[1] + box[3], measure, style, rules)
  lines <- key_lines(rows, x, right, measure, style, rules)
  line <- line_height(style, "label")
  side <- style$swatch * base
  pitches <- vapply(lines, length, integer(1)) * line + rules$key_row_gap * base
  top <- max(box[2], cy - sum(pitches) / 2)
  shapes <- list()
  for (index in seq_along(rows)) {
    row <- rows[[index]]
    centre <- top + (line + rules$key_row_gap * base) / 2
    left <- x + row$depth * rules$key_indent * base
    shapes[[length(shapes) + 1]] <- key_square(left, centre - side / 2, side, row$segment$color)
    for (number in seq_along(lines[[index]])) {
      shapes[[length(shapes) + 1]] <- shape_text(left + side + style$swatch_text * base,
                                                 baseline_for(centre + (number - 1) * line, style, "label"),
                                                 lines[[index]][number], "label", style$neutral$ink)
    }
    shapes[[length(shapes) + 1]] <- shape_text(right, baseline_for(centre, style, "label"), row$segment$share_text,
                                               "label", style$neutral$muted, "right")
    top <- top + pitches[index]
  }
  shapes
}

inside_sector <- function(point, centre, radii, span, pad) {
  dx <- point[1] - centre[1]
  dy <- centre[2] - point[2]
  radius <- sqrt(dx^2 + dy^2)
  if (radius < radii[1] + pad || radius > radii[2] - pad) return(FALSE)
  angle_pad <- degrees(pad / radius)
  offset <- (span[1] - angle_pad - degrees(atan2(dy, dx))) %% 360
  offset <= span[1] - span[2] - 2 * angle_pad
}

text_fits <- function(x, y, width, height, centre, radii, span, pad) {
  steps <- (0:4) / 4
  left <- x - width / 2
  top <- y - height / 2
  outline <- c(lapply(steps, function(step) c(left + width * step, top)),
               lapply(steps, function(step) c(left + width * step, top + height)),
               lapply(steps, function(step) c(left, top + height * step)),
               lapply(steps, function(step) c(left + width, top + height * step)))
  all(vapply(outline, inside_sector, logical(1), centre = centre, radii = radii, span = span, pad = pad))
}

ring_label <- function(segment, span, radii, cx, cy, measure, style, rules) {
  if (segment$share < rules$ring_min_share) return(list())
  position <- donut_point(cx, cy, mean(radii), mean(span))
  height <- style$cap_height * style$sizes$label
  pad <- rules$ring_label_pad * style$base
  candidates <- c(paste(segment$name, segment$share_text), segment$share_text)
  fitting <- Filter(function(content) {
    text_fits(position[1], position[2], measure(content, "label"), height, c(cx, cy), radii, span, pad)
  }, candidates)
  if (!length(fitting)) return(list())
  neutral <- style$neutral
  colour <- if (contrast_ratio(segment$color, neutral$ink) >= contrast_ratio(segment$color, neutral$surface)) {
    neutral$ink
  } else {
    neutral$surface
  }
  list(shape_text(position[1], baseline_for(position[2], style, "label"), fitting[[1]], "label", colour, "center"))
}

ring_labels <- function(rings, radii, cx, cy, measure, style, rules) {
  shapes <- list()
  for (ring_index in seq_along(rings)) {
    spans <- ring_spans(rings[[ring_index]])
    for (index in seq_along(rings[[ring_index]])) {
      shapes <- c(shapes, ring_label(rings[[ring_index]][[index]], spans[[index]], radii[[ring_index]], cx, cy,
                                     measure, style, rules))
    }
  }
  shapes
}

donut_drawing <- function(spec, box, measure, style) {
  rules <- hl_tokens()$donut
  rings <- spec$rings
  base <- style$base
  if (spec$labels == "outside") {
    side <- outside_width(rings[[1]], measure, style, rules)
    radius <- max(min(box[4] / 2, (box[3] - 2 * side) / 2), rules$min_radius * base)
    cx <- box[1] + box[3] / 2
  } else if (spec$labels == "key") {
    radius <- min(box[4] / 2, box[3] * rules$key_share / 2)
    cx <- box[1] + radius
  } else {
    radius <- min(box[3], box[4]) / 2
    cx <- box[1] + box[3] / 2
  }
  cy <- box[2] + box[4] / 2
  radii <- ring_radii(length(rings), radius, if (length(rings) == 1) rules$hole else rules$hole_nested, rules$gap_pt)
  shapes <- segment_shapes(rings, cx, cy, radii, rules)
  labels <- switch(spec$labels,
                   outside = outside_labels(rings[[1]], cx, cy, radius, box, measure, style, rules,
                                            lines = outside_lines(rings[[1]], box, radius, measure, style, rules,
                                                                  "donut")),
                   key = hierarchical_key(rings, cx + radius + rules$key_gap * base, box, cy, measure, style, rules),
                   ring_labels(rings, radii, cx, cy, measure, style, rules))
  label <- spec$total_label
  labelled <- !is.null(spec$total) && !is.null(label) && nzchar(label)
  lines <- if (labelled) total_lines(label, radii[[1]][1], measure, style) else NULL
  c(shapes, labels, centre_total(spec$total, label, cx, cy, style, lines))
}
