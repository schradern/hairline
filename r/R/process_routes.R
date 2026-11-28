# Flows of a process diagram in pt: straight up or down within a stage, otherwise out of the right edge and into the
# left edge, turning in the gap before the target (or, when a step blocks its own lane, in the gap after the source),
# with rounded corners and a small filled head. Mirrors the Python package's charts/process_routes.py.

# A corner rounded as a quadratic curve from `radius` before the vertex to `radius` after it. As Python's corner().
process_corner <- function(before, vertex, after, radius, steps) {
  into <- sqrt(sum((before - vertex)^2))
  out <- sqrt(sum((vertex - after)^2))
  room <- min(radius, into / 2, out / 2)
  if (room <= 0) return(matrix(vertex, nrow = 1))
  start <- vertex + room * (before - vertex) / into
  end <- vertex + room * (after - vertex) / out
  t <- (0:steps) / steps
  cbind((1 - t)^2 * start[1] + 2 * (1 - t) * t * vertex[1] + t^2 * end[1],
        (1 - t)^2 * start[2] + 2 * (1 - t) * t * vertex[2] + t^2 * end[2])
}

process_rounded <- function(points, radius, steps) {
  inner <- lapply(seq_len(nrow(points) - 2) + 1, function(index) {
    process_corner(points[index - 1, ], points[index, ], points[index + 1, ], radius, steps)
  })
  do.call(rbind, c(list(points[1, , drop = FALSE]), inner, list(points[nrow(points), , drop = FALSE])))
}

# The path stopped short by the head's length, and the head: a triangle pointing along the last segment. As
# Python's head().
process_head <- function(points, size) {
  end <- points[nrow(points), ]
  before <- points[nrow(points) - 1, ]
  along <- (end - before) / sqrt(sum((end - before)^2))
  base <- end - size * along
  across <- c(-along[2], along[1]) * size / 2
  list(line = rbind(points[-nrow(points), , drop = FALSE], base),
       tip = rbind(end, base + across, base - across, deparse.level = 0))
}

process_free <- function(cells, lanes, stages) {
  if (!length(lanes) || !length(stages)) return(TRUE)
  !any(paste(lanes, stages) %in% cells)
}

process_between <- function(first, last) if (last - first < 2) numeric() else seq(first + 1, last - 1)

# How a flow runs between two steps (their lane and stage) without crossing another step: "vertical" within a stage,
# "straight" along a lane, turning "before" the target or "after" the source; an error when every way crosses a step.
# As Python's route_kind().
process_route_kind <- function(source, target, cells, where) {
  kind <- if (source$stage == target$stage) {
    lanes <- process_between(min(source$lane, target$lane), max(source$lane, target$lane))
    if (process_free(cells, lanes, source$stage)) "vertical"
  } else {
    between <- process_between(source$stage, target$stage)
    if (source$lane == target$lane) {
      if (process_free(cells, source$lane, between)) "straight"
    } else if (process_free(cells, source$lane, between)) {
      "before"
    } else if (process_free(cells, target$lane, between)) {
      "after"
    }
  }
  if (is.null(kind)) {
    stop(sprintf(paste0("hairline: process: the flow from '%s' to '%s' would cross another step%s; move one of them ",
                        "to another stage or lane"), source$name, target$name, where), call. = FALSE)
  }
  kind
}

# The corner points of a flow from step `source` to step `target` (their boxes and cells). As Python's path().
process_path <- function(source, target, cells, turns, where) {
  kind <- process_route_kind(source, target, cells, where)
  if (kind == "vertical") {
    down <- target$lane > source$lane
    return(rbind(c(source$cx, if (down) source$bottom else source$top),
                 c(target$cx, if (down) target$top else target$bottom)))
  }
  if (kind == "straight") return(rbind(c(source$right, source$cy), c(target$left, target$cy)))
  turn <- if (kind == "before") turns[target$stage] else turns[source$stage + 1]
  rbind(c(source$right, source$cy), c(turn, source$cy), c(turn, target$cy), c(target$left, target$cy))
}

# The flow's label in muted text on a surface halo: above where it leaves its step, or right of a flow within a
# stage. As Python's flow_label().
process_flow_label <- function(flow, source, target, measure, style, rules, offset) {
  if (!nzchar(flow$label)) return(list())
  size <- style$sizes$label
  pad <- rules$label_pad * style$base
  halo <- rules$halo_pad * style$base
  if (source$stage == target$stage) {
    ends <- sort(if (target$lane > source$lane) c(source$bottom, target$top) else c(target$bottom, source$top))
    x <- source$cx + pad
    y <- mean(ends) + style$cap_height * size / 2
  } else {
    x <- source$right + pad + offset
    y <- source$cy - pad - style$descender * size
  }
  left <- x - halo
  right <- x + measure(flow$label, "label") + halo
  upper <- y - style$cap_height * size - halo
  lower <- y + style$descender * size + halo
  list(list(kind = "polygon", points = rbind(c(left, upper), c(right, upper), c(right, lower), c(left, lower)),
            fill = style$neutral$surface, role = "halo"),
       c(shape_text(x, y, flow$label, "label", style$neutral$muted), part = "flow_label"))
}

# A flow's line and head: faint, in the accent and thicker when highlighted, dashed when tentative. As Python's
# flow_shapes().
process_flow_shapes <- function(flow, places, cells, turns, style, rules, accent, where) {
  source <- places[[flow$source + 1]]
  target <- places[[flow$target + 1]]
  base <- style$base
  points <- process_rounded(process_path(source, target, cells, turns, where), rules$corner * base,
                            rules$corner_steps)
  arrow <- process_head(points, rules$arrow_head * base)
  highlight <- identical(flow$status, "highlight")
  colour <- if (highlight) accent else style$neutral$faint
  stroke <- list(kind = "line", points = unname(arrow$line), color = colour,
                 width = if (highlight) rules$highlight_width * base else style$leader_width, role = "flow")
  if (identical(flow$status, "tentative")) stroke$dash <- unlist(rules$dash)
  list(stroke, list(kind = "polygon", points = unname(arrow$tip), fill = colour, role = "flow_head"))
}
