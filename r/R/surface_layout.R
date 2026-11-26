# Surface labels, fit and shapes, mirroring the Python charts/surface_geometry.py (see surface_geometry.R).

# Tick labels and the title of the x or y axis, set off outward from the floor's centre. As Python's floor_labels().
surface_floor_labels <- function(scene, frame, project, axis) {
  floor <- frame$floor
  near <- frame$near
  edge <- if (axis == "x") function(at) c(at, near[2], floor) else function(at) c(near[1], at, floor)
  middle <- project(edge(0))
  centre <- project(c(0, 0, floor))
  direction <- surface_unit(middle[1:2] - centre[1:2])
  gap <- scene$gap
  placed <- surface_placement(direction, scene)
  ticks <- lapply(scene$ticks[[axis]], function(tick) {
    surface_label(project(edge(tick$at)), direction * gap, tick$text, tick$width, scene$text$ticks, "tick", placed)
  })
  title <- scene$titles[[axis]]
  if (!nzchar(title$text)) return(ticks)
  across <- surface_normal(project(edge(-1)), project(edge(1)), direction)
  away <- 2 * gap + surface_reach(across, ticks, scene)
  c(ticks, list(surface_label(middle, across * away, title$text, title$width, scene$text$titles, "title",
                              surface_placement(across, scene))))
}

# The unit normal of an edge on the page, on the side `direction` points to. As Python's normal().
surface_normal <- function(start, end, direction) {
  run <- end[1:2] - start[1:2]
  if (sqrt(sum(run^2)) < surface_short) return(direction)
  across <- surface_unit(c(-run[2], run[1]))
  if (sum(across * direction) >= 0) across else -across
}

# Tick labels of the z axis beside its edge, away from the cube, and its title above them. As Python's
# height_labels().
surface_height_labels <- function(scene, frame, project) {
  corner <- frame$z_corner
  gap <- scene$gap
  glyphs <- scene$text
  side <- if (project(c(corner, frame$floor))[1] <= 0) -1 else 1
  placed <- list(align = if (side < 0) "right" else "left", shift = glyphs$cap / 2)
  ticks <- lapply(scene$ticks$z, function(tick) {
    surface_label(project(c(corner, tick$at)), c(side * gap, 0), tick$text, tick$width, glyphs$ticks, "tick", placed)
  })
  title <- scene$titles$z
  if (!nzchar(title$text)) return(ticks)
  rise <- -(glyphs$cap / 2 + gap + glyphs$descender)
  c(ticks, list(surface_label(project(c(corner, frame$top)), c(side * gap, rise), title$text, title$width,
                              glyphs$titles, "title", list(align = placed$align, shift = 0))))
}

# A label's extent in pt around its scaled point: c(left, right) and c(top, bottom). As Python's label_span().
surface_label_span <- function(item, scene) {
  share <- c(left = 0, center = 0.5, right = 1)[[item$align]]
  left <- item$offset[1] - share * item$width
  baseline <- item$offset[2] + item$shift
  list(c(left, left + item$width), c(baseline - scene$text$cap, baseline + scene$text$descender))
}

# Where points with fixed extents start and end at `scale`; items is a matrix of (point, low, high) rows.
surface_extent <- function(items, scale) c(min(scale * items[, 1] + items[, 2]), max(scale * items[, 1] + items[, 3]))

# The largest scale at which the items span at most `room`. As Python's largest_scale().
surface_largest_scale <- function(items, room) {
  scale <- Inf
  for (i in seq_len(nrow(items))) {
    for (j in seq_len(nrow(items))) {
      spread <- items[i, 1] - items[j, 1]
      if (spread > surface_short) scale <- min(scale, (room - items[i, 3] + items[j, 2]) / spread)
    }
  }
  span <- surface_extent(items, scale)
  if (span[2] - span[1] <= room + 1e-6) scale else -Inf
}

# Scale and offset that fit the cube's corners and every label into the box: as large as the tighter side allows,
# centred across and set at the top. As Python's fitted().
surface_fitted <- function(scene, box, corners, labels) {
  spans <- lapply(labels, surface_label_span, scene = scene)
  rows <- function(index) {
    rbind(do.call(rbind, lapply(corners, function(corner) c(corner[index], 0, 0))),
          do.call(rbind, lapply(seq_along(labels), function(k) c(labels[[k]]$at[index], spans[[k]][[index]]))))
  }
  across <- rows(1)
  down <- rows(2)
  scale <- min(surface_largest_scale(across, box[3]), surface_largest_scale(down, box[4]))
  if (!(scale > 0) || is.infinite(scale)) {
    stop(sprintf(paste("hairline: surface: the axis labels leave no room for the surface in %.0f x %.0f pt.",
                       "Shorten the axis titles or use a wider size"), box[3], box[4]), call. = FALSE)
  }
  horizontal <- surface_extent(across, scale)
  vertical <- surface_extent(down, scale)
  list(scale = scale, offset = c(box[1] + (box[3] - diff(horizontal)) / 2 - horizontal[1], box[2] - vertical[1]))
}

# One polygon per cell with four values, far to near; its seams drawn in its own colour. As Python's cell_shapes().
surface_cell_shapes <- function(scene, project, place) {
  xs <- unlist(scene$xs)
  ys <- unlist(scene$ys)
  cells <- list()
  for (row in seq_len(length(ys) - 1)) {
    for (column in seq_len(length(xs) - 1)) {
      fill <- scene$fills[[row]][[column]]
      if (is.null(fill)) next
      corners <- list(c(column, row), c(column + 1, row), c(column + 1, row + 1), c(column, row + 1))
      projected <- lapply(corners, function(at) project(c(xs[at[1]], ys[at[2]], scene$zs[[at[2]]][[at[1]]])))
      depth <- round(mean(vapply(projected, `[`, 0, 3)), surface_depth_digits)
      cells[[length(cells) + 1]] <- list(depth = depth, fill = fill, projected = projected)
    }
  }
  if (!length(cells)) return(list())
  depths <- vapply(cells, `[[`, 0, "depth")
  lapply(cells[order(-depths, seq_along(cells))], function(cell) {
    list(kind = "polygon", points = do.call(rbind, lapply(cell$projected, place)), fill = cell$fill,
         edge = cell$fill, edge_width = scene$seam, part = "cell")
  })
}

# The scene from `view` (its own by default), fitted into the box: lines, then cells far to near, then texts. As
# Python's scene_shapes().
surface_scene_shapes <- function(scene, box, view = NULL) {
  project <- surface_projector(view %||% scene$view)
  frame <- surface_cube_frame(scene, project)
  labels <- c(surface_floor_labels(scene, frame, project, "x"), surface_floor_labels(scene, frame, project, "y"),
              surface_height_labels(scene, frame, project))
  corners <- list()
  for (z in c(frame$floor, frame$top)) for (y in c(-1, 1)) for (x in c(-1, 1)) {
    corners[[length(corners) + 1]] <- project(c(x, y, z))
  }
  fit <- surface_fitted(scene, box, corners, labels)
  place <- function(point) fit$offset + fit$scale * point[1:2]
  lines <- lapply(surface_frame_lines(scene, frame), function(line) {
    list(kind = "line", points = do.call(rbind, lapply(line$segment, function(end) place(project(end)))),
         color = scene$lines[[line$kind]], width = scene$lines[[paste0(line$kind, "_width")]])
  })
  texts <- lapply(labels, function(item) {
    at <- place(item$at) + item$offset
    c(shape_text(at[1], at[2] + item$shift, item$text, "label", item$color, item$align), part = item$part)
  })
  c(lines, surface_cell_shapes(scene, project, place), texts)
}

# The lowest point the shapes reach: outlines, and texts down to their descenders. As Python's shapes_bottom().
surface_shapes_bottom <- function(shapes, descender) {
  max(vapply(shapes, function(shape) {
    if (shape$kind == "text") shape$y + descender else max(shape_points(shape)[, 2])
  }, 0))
}

# The surface on the left share of the box and its heatmap on the right, as tall as the surface. As Python's
# pair_layout().
surface_pair_layout <- function(scene, flat, box) {
  split <- scene$pair
  room <- box[3] - split$gap
  left <- c(box[1], box[2], room * split$share, box[4])
  surface <- surface_scene_shapes(scene, left)
  height <- surface_shapes_bottom(surface, scene$text$descender) - box[2]
  right <- c(left[1] + left[3] + split$gap, box[2], room - left[3], height)
  heat <- heatmap_layout(flat, right, height = height, tag = FALSE)
  list(shapes = c(surface, heat$shapes), box = left, flat_box = right, cells = heat$cells)
}
