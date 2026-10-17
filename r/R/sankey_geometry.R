# Sankey geometry in pt, the same algorithm as the Python package's sankey_geometry.

barycentre_order <- function(nodes, links, previous) {
  centres <- vapply(nodes, function(node) {
    incoming <- Filter(function(link) link$target == node$name, links)
    total <- sum(vapply(incoming, `[[`, numeric(1), "value"))
    if (total == 0) return(Inf)
    centre <- sum(vapply(incoming, function(link) {
      link$value * (previous[[link$source]][1] + previous[[link$source]][2]) / 2
    }, numeric(1))) / total
    round(centre, 6)
  }, numeric(1))
  nodes[order(centres, seq_along(nodes))]
}

sankey_stack <- function(nodes, top, height, scale, gap) {
  values <- vapply(nodes, `[[`, numeric(1), "value")
  y <- top + (height - sum(values) * scale - gap * (length(nodes) - 1)) / 2
  positions <- list()
  for (node in nodes) {
    positions[[node$name]] <- c(y, y + node$value * scale)
    y <- y + node$value * scale + gap
  }
  positions
}

sankey_place <- function(spec, top, height, gap) {
  columns <- spec$nodes
  scale <- min(vapply(columns, function(nodes) {
    (height - gap * (length(nodes) - 1)) / sum(vapply(nodes, `[[`, numeric(1), "value"))
  }, numeric(1)))
  ordered <- list(columns[[1]])
  positions <- list(sankey_stack(columns[[1]], top, height, scale, gap))
  for (index in seq_along(columns)[-1]) {
    links <- Filter(function(link) link$column == index - 2, spec$links)
    ordered[[index]] <- barycentre_order(columns[[index]], links, positions[[index - 1]])
    positions[[index]] <- sankey_stack(ordered[[index]], top, height, scale, gap)
  }
  list(ordered = ordered, positions = positions, scale = scale)
}

sankey_bezier <- function(start, end, count) {
  middle <- (start[1] + end[1]) / 2
  t <- (0:count) / count
  cbind((1 - t)^3 * start[1] + 3 * (1 - t)^2 * t * middle + 3 * (1 - t) * t^2 * middle + t^3 * end[1],
        ((1 - t)^3 + 3 * (1 - t)^2 * t) * start[2] + (3 * (1 - t) * t^2 + t^3) * end[2])
}

link_offsets <- function(links, end, other, here, there, groups, scale) {
  keys <- vapply(links, function(link) there[[link[[other]]]][1], numeric(1))
  ranks <- vapply(links, function(link) match(link$group, groups), integer(1))
  offsets <- numeric(length(links))
  filled <- list()
  for (index in order(keys, ranks, seq_along(links))) {
    node <- links[[index]][[end]]
    start <- filled[[node]] %||% here[[node]][1]
    offsets[index] <- start
    filled[[node]] <- start + links[[index]]$value * scale
  }
  offsets
}

sankey_link_shapes <- function(spec, positions, xs, width, scale, rules) {
  shapes <- list()
  for (index in seq_len(length(positions) - 1)) {
    links <- Filter(function(link) link$column == index - 1, spec$links)
    tops <- link_offsets(links, "source", "target", positions[[index]], positions[[index + 1]], spec$groups, scale)
    ends <- link_offsets(links, "target", "source", positions[[index + 1]], positions[[index]], spec$groups, scale)
    start_x <- xs[index] + width
    end_x <- xs[index + 1]
    for (item in seq_along(links)) {
      link <- links[[item]]
      thickness <- link$value * scale
      outline <- rbind(sankey_bezier(c(start_x, tops[item]), c(end_x, ends[item]), rules$curve_points),
                       sankey_bezier(c(end_x, ends[item] + thickness), c(start_x, tops[item] + thickness),
                                     rules$curve_points))
      shapes[[length(shapes) + 1]] <- list(kind = "polygon", points = outline, fill = link$color,
                                           alpha = rules$link_opacity, role = "link", column = index - 1,
                                           source = link$source, target = link$target)
    }
  }
  shapes
}
