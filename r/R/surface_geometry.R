# Surface geometry in pt, mirroring the Python charts/surface_geometry.py: a grid of values seen from a viewpoint
# (orthographic projection), drawn back to front as flat polygons over a floor and two back walls, with ticks on the
# edges nearest the viewer. The scene is the view-independent part; surface_scene_shapes() projects it for one view
# and fits it into the plot box. The shared interactive script draws the same scene again as the reader turns it.

surface_axes <- c("x", "y", "z")
# Depths are rounded before sorting so the order of equally deep cells is the same in Python, R and the browser.
surface_depth_digits <- 9
# A direction shorter than this has no side (an edge seen end on); its labels go below it.
surface_short <- 1e-9

# The spec with every text's width in pt and the colours and sizes the drawing needs. As Python's surface_scene().
surface_scene <- function(spec, measure, style) {
  rules <- hl_tokens()$surface
  neutral <- style$neutral
  size <- style$sizes$label
  ticks <- lapply(stats::setNames(nm = surface_axes), function(axis) {
    lapply(spec$ticks[[axis]], function(tick) c(tick, list(width = measure(tick$text, "label"))))
  })
  titles <- lapply(spec$titles, function(title) {
    list(text = title, width = if (nzchar(title)) measure(title, "label") else 0)
  })
  list(xs = spec$xs, ys = spec$ys, zs = spec$zs, fills = spec$fills, height = spec$height, view = spec$view,
       ticks = ticks, titles = titles,
       text = list(size = size, cap = style$cap_height * size, descender = style$descender * size,
                   ticks = neutral$faint, titles = neutral$muted),
       lines = list(axis = neutral$axis, grid = neutral$grid, axis_width = style$axis_width, grid_width = style$grid),
       gap = hl_tokens()$spacing$y_labels_plot * style$base, align = rules$align, seam = rules$seam_pt,
       pair = list(share = rules$pair_share, gap = rules$pair_gap * style$base))
}

# Cube point -> c(across, down, depth): turned by the azimuth, tilted by the elevation. As Python's projector().
surface_projector <- function(view) {
  azimuth <- view$azimuth * pi / 180
  elevation <- view$elevation * pi / 180
  function(point) {
    across <- point[1] * cos(azimuth) - point[2] * sin(azimuth)
    back <- point[1] * sin(azimuth) + point[2] * cos(azimuth)
    c(across, -(point[3] * cos(elevation) + back * sin(elevation)), back * cos(elevation) - point[3] * sin(elevation))
  }
}

# Which edges carry the axes in this view. As Python's cube_frame().
surface_cube_frame <- function(scene, project) {
  floor <- -scene$height / 2
  corners <- list(c(-1, -1), c(1, -1), c(-1, 1), c(1, 1))
  depths <- vapply(corners, function(corner) round(project(c(corner, floor))[3], surface_depth_digits), 0)
  near <- corners[[which.min(depths)]]
  sides <- list(c(-near[1], near[2]), c(near[1], -near[2]))
  across <- vapply(sides, function(corner) round(project(c(corner, floor))[1], surface_depth_digits), 0)
  chosen <- which.min(across)
  list(floor = floor, top = -floor, near = near, z_corner = sides[[chosen]], other_corner = sides[[3 - chosen]],
       far = -near)
}

# Segments of the floor, the two back walls and the three axes, each with its line kind. As Python's frame_lines().
surface_frame_lines <- function(scene, frame) {
  floor <- frame$floor
  top <- frame$top
  near <- frame$near
  far <- frame$far
  at <- function(axis) vapply(scene$ticks[[axis]], function(tick) tick$at, 0)
  grid <- c(lapply(at("x"), function(v) list(c(v, -1, floor), c(v, 1, floor))),
            lapply(at("y"), function(v) list(c(-1, v, floor), c(1, v, floor))),
            lapply(at("z"), function(v) list(c(far[1], -1, v), c(far[1], 1, v))),
            lapply(at("z"), function(v) list(c(-1, far[2], v), c(1, far[2], v))),
            list(list(c(far[1], -1, floor), c(far[1], 1, floor)), list(c(-1, far[2], floor), c(1, far[2], floor))),
            lapply(list(far, frame$other_corner), function(corner) list(c(corner, floor), c(corner, top))))
  axes <- list(list(c(-1, near[2], floor), c(1, near[2], floor)), list(c(near[1], -1, floor), c(near[1], 1, floor)),
               list(c(frame$z_corner, floor), c(frame$z_corner, top)))
  c(lapply(grid, function(segment) list(segment = segment, kind = "grid")),
    lapply(axes, function(segment) list(segment = segment, kind = "axis")))
}

surface_unit <- function(vector) {
  length <- sqrt(sum(vector^2))
  if (length < surface_short) c(0, 1) else vector / length
}

# Alignment and baseline shift of a text set off along `direction`. As Python's placement().
surface_placement <- function(direction, scene) {
  threshold <- scene$align
  glyphs <- scene$text
  align <- if (direction[1] > threshold) "left" else if (direction[1] < -threshold) "right" else "center"
  shift <- if (direction[2] > threshold) glyphs$cap else if (direction[2] < -threshold) -glyphs$descender else
    glyphs$cap / 2
  list(align = align, shift = shift)
}

surface_label <- function(point, offset, content, width, colour, part, placed) {
  list(at = point[1:2], offset = offset, text = content, width = width, color = colour, part = part,
       align = placed$align, shift = placed$shift)
}

# How far the widest of `labels` reaches along `direction`. As Python's reach().
surface_reach <- function(direction, labels, scene) {
  tall <- scene$text$cap + scene$text$descender
  if (!length(labels)) return(0)
  max(vapply(labels, function(item) abs(direction[1]) * item$width + abs(direction[2]) * tall, 0))
}
