# Venn diagram geometry in pt, mirroring the Python venn_geometry: two or three circles at fixed schematic
# positions (or, for two sets, areas proportional to the counts), each region's count inside it and the set names
# outside.

venn_centres <- list(`2` = list(c(-0.5, 0), c(0.5, 0)), `3` = list(c(-0.5, 0.33), c(0.5, 0.33), c(0, -0.5)))
venn_name_angles <- c(150, 30, 270)
venn_region_points <- list(`0` = c(-0.95, 0.65), `1` = c(0.95, 0.65), `2` = c(0, -1.05), `0 1` = c(0, 0.75),
                           `0 2` = c(-0.6, -0.35), `1 2` = c(0.6, -0.35), `0 1 2` = c(0, 0.05))

lens_area <- function(first, second, distance) {
  if (distance >= first + second) return(0)
  if (distance <= abs(first - second)) return(pi * min(first, second)^2)
  one <- max(-1, min(1, (distance^2 + first^2 - second^2) / (2 * distance * first)))
  two <- max(-1, min(1, (distance^2 + second^2 - first^2) / (2 * distance * second)))
  kite <- (-distance + first + second) * (distance + first - second) * (distance - first + second) *
    (distance + first + second)
  first^2 * acos(one) + second^2 * acos(two) - 0.5 * sqrt(max(0, kite))
}

venn_separation <- function(first, second, area, rules) {
  if (area <= 0) return(first + second + rules$apart)
  low <- abs(first - second)
  high <- first + second
  for (step in seq_len(rules$iterations)) {
    middle <- (low + high) / 2
    if (lens_area(first, second, middle) > area) low <- middle else high <- middle
  }
  (low + high) / 2
}

venn_unit_circles <- function(spec, rules) {
  if (!isTRUE(spec$proportional)) {
    return(lapply(venn_centres[[as.character(length(spec$sets))]], function(centre) c(centre, 1)))
  }
  sizes <- vapply(spec$sets, function(entry) as.numeric(entry$value), numeric(1))
  first <- sqrt(sizes[1] / max(sizes))
  second <- sqrt(sizes[2] / max(sizes))
  distance <- venn_separation(first, second, pi * as.numeric(spec$regions[[3]]$value) / max(sizes), rules)
  list(c(-distance / 2, 0, first), c(distance / 2, 0, second))
}

venn_region_point <- function(members, circles) {
  key <- paste(members, collapse = " ")
  if (length(circles) == 3) return(venn_region_points[[key]])
  one <- circles[[1]]
  two <- circles[[2]]
  edges <- switch(key, `0` = c(one[1] - one[3], two[1] - two[3]), `1` = c(one[1] + one[3], two[1] + two[3]),
                  `0 1` = c(two[1] - two[3], one[1] + one[3]))
  c(sum(edges) / 2, 0)
}

# Name in ink and size in muted, set off the circle in the direction of `angle`; a wrapped name takes `lines`,
# aligned away from the circle, with the size after the last (alone after an empty last line).
venn_name_label <- function(entry, lines, circle, angle, scale, origin, measure, style, rules) {
  cosine <- cos(angle * pi / 180)
  sine <- sin(angle * pi / 180)
  gap <- rules$label_gap * style$base
  size <- style$sizes$label
  x <- origin[1] + (circle[1] + cosine * circle[3]) * scale + cosine * gap
  y <- origin[2] - (circle[2] + sine * circle[3]) * scale - sine * gap
  space <- hl_tokens()$donut$label_space * size
  line <- line_height(style, "label")
  count <- length(lines)
  value <- measure(entry$value_text, "label")
  widths <- vapply(lines, measure, numeric(1), role = "label", USE.NAMES = FALSE)
  widths[count] <- if (nzchar(lines[count])) widths[count] + space + value else value
  cutoff <- rules$side_cutoff
  first <- if (sine > cutoff) {
    y - style$descender * size - (count - 1) * line
  } else if (sine < -cutoff) {
    y + style$cap_height * size
  } else {
    baseline_for(y - (count - 1) * line / 2, style, "label")
  }
  starts <- if (cosine < -cutoff) x - widths else if (cosine > cutoff) rep(x, count) else x - widths / 2
  shapes <- list()
  for (index in seq_len(count)) {
    if (!nzchar(lines[index])) next
    shapes[[length(shapes) + 1]] <- shape_text(starts[index], first + (index - 1) * line, lines[index], "label",
                                               style$neutral$ink)
  }
  c(shapes, list(shape_text(starts[count] + widths[count] - value, first + (count - 1) * line, entry$value_text,
                            "label", style$neutral$muted)))
}

venn_shapes <- function(spec, circles, scale, origin, measure, style, rules, names = NULL) {
  fills <- outlines <- labels <- list()
  for (index in seq_along(spec$sets)) {
    entry <- spec$sets[[index]]
    circle <- circles[[index]]
    points <- donut_arc(origin[1] + circle[1] * scale, origin[2] - circle[2] * scale, circle[3] * scale, 90, -270,
                        rules$arc_step)
    fills[[index]] <- tagged_shape(list(kind = "polygon", role = "set", name = entry$name, points = points,
                                        fill = entry$color, alpha = rules$fill_opacity),
                                   entry$name, paste0(entry$name, ": ", entry$value_text))
    outlines[[index]] <- list(kind = "line", points = points, width = style$data_width,
                              color = point_fill(entry$color, style$neutral$surface))
  }
  for (region in spec$regions) {
    if (isTRUE(spec$proportional) && region$value == 0) next
    point <- venn_region_point(unlist(region$sets), circles)
    labels[[length(labels) + 1]] <- shape_text(origin[1] + point[1] * scale,
                                               baseline_for(origin[2] - point[2] * scale, style, "label"),
                                               region$value_text, "label", style$neutral$ink, "center")
  }
  names <- names %||% lapply(spec$sets, `[[`, "name")
  for (index in seq_along(spec$sets)) {
    labels <- c(labels, venn_name_label(spec$sets[[index]], names[[index]], circles[[index]], venn_name_angles[index],
                                        scale, origin, measure, style, rules))
  }
  c(fills, outlines, labels)
}

venn_bounds <- function(shapes, measure, style) {
  xs <- ys <- numeric()
  for (shape in shapes) {
    if (shape$kind == "text") {
      width <- measure(shape$text, shape$role)
      size <- style$sizes[[shape$role]]
      left <- shape$x - switch(shape$align, left = 0, center = width / 2, right = width)
      xs <- c(xs, left, left + width)
      ys <- c(ys, shape$y - style$cap_height * size, shape$y + style$descender * size)
    } else {
      xs <- c(xs, shape$points[, 1])
      ys <- c(ys, shape$points[, 2])
    }
  }
  c(min(xs), min(ys), max(xs), max(ys))
}

# Set names wrapped so that each line, the last with its size, is at most `width` wide.
venn_wrapped_names <- function(spec, width, measure, style) {
  space <- hl_tokens()$donut$label_space * style$sizes$label
  lapply(spec$sets, function(entry) pair_lines(entry$name, width, measure, measure(entry$value_text, "label"), space))
}

# One line per name while the diagram is narrow enough with circles of the minimum radius (`fits`); otherwise the
# widest wrap that is, or NULL when even a word per line is too wide.
venn_name_lines <- function(spec, fits, measure, style, rules) {
  space <- hl_tokens()$donut$label_space * style$sizes$label
  names <- lapply(spec$sets, `[[`, "name")
  if (fits(names)) return(names)
  narrowest <- venn_wrapped_names(spec, 0, measure, style)
  if (!fits(narrowest)) return(NULL)
  widest <- function(sets) {
    max(vapply(seq_along(spec$sets), function(index) {
      pair_width(sets[[index]], measure, measure(spec$sets[[index]]$value_text, "label"), space)
    }, numeric(1)))
  }
  low <- widest(narrowest)
  high <- widest(names)
  for (step in seq_len(rules$iterations)) {
    middle <- (low + high) / 2
    if (fits(venn_wrapped_names(spec, middle, measure, style))) low <- middle else high <- middle
  }
  venn_wrapped_names(spec, low, measure, style)
}

# Names wrap when the circles would fall below the minimum radius; a diagram taller than the panel starts at its top
# and the figure grows.
venn_drawing <- function(spec, box, measure, style) {
  rules <- hl_tokens()$venn
  circles <- venn_unit_circles(spec, rules)
  bounds <- function(scale, names) {
    venn_bounds(venn_shapes(spec, circles, scale, c(0, 0), measure, style, rules, names), measure, style)
  }
  narrow <- function(scale, names) {
    edges <- bounds(scale, names)
    edges[3] - edges[1] <= box[3]
  }
  fits <- function(scale, names) {
    edges <- bounds(scale, names)
    edges[3] - edges[1] <= box[3] && edges[4] - edges[2] <= box[4]
  }
  low <- hl_tokens()$donut$min_radius * style$base
  high <- max(box[3], box[4])
  names <- venn_name_lines(spec, function(lines) narrow(low, lines), measure, style, rules)
  if (is.null(names)) {
    edges <- bounds(low, venn_wrapped_names(spec, 0, measure, style))
    stop(sprintf(paste("hairline: venn: the set names need %.0f pt across beside circles of the smallest size, but",
                       "the figure leaves %.0f pt. Shorten the set names or use a wider size"),
                 edges[3] - edges[1], box[3]), call. = FALSE)
  }
  if (fits(low, names)) {
    for (step in seq_len(rules$iterations)) {
      middle <- (low + high) / 2
      if (fits(middle, names)) low <- middle else high <- middle
    }
  }
  edges <- bounds(low, names)
  origin <- c(box[1] + (box[3] - (edges[3] - edges[1])) / 2 - edges[1],
              box[2] + max(0, box[4] - (edges[4] - edges[2])) / 2 - edges[2])
  venn_shapes(spec, circles, low, origin, measure, style, rules, names)
}
