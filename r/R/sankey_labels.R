# Sankey nodes, labels, headings and the entry point sankey_drawing().

sankey_node_shapes <- function(ordered, positions, xs, width) {
  shapes <- list()
  for (index in seq_along(ordered)) {
    for (node in ordered[[index]]) {
      span <- positions[[index]][[node$name]]
      x <- xs[index]
      shapes[[length(shapes) + 1]] <- tagged_shape(list(kind = "polygon", fill = node$color, role = "node",
                                                        name = node$name,
                                                        points = rbind(c(x, span[1]), c(x + width, span[1]),
                                                                       c(x + width, span[2]), c(x, span[2]))),
                                                   node$name, paste0(node$name, ": ", node$value_text))
    }
  }
  shapes
}

sankey_label_space <- function(style) hl_tokens()$donut$label_space * style$sizes$label

# Each node's name in lines no wider than `room`, its value following the last; a list by node name.
sankey_node_lines <- function(nodes, room, measure, style) {
  lines <- lapply(nodes, function(node) {
    fit_lines(node$name, room, measure, "sankey", "the label", measure(node$value_text, "label"),
              sankey_label_space(style))
  })
  stats::setNames(lines, vapply(nodes, `[[`, character(1), "name"))
}

sankey_block_width <- function(node, lines, measure, style) {
  pair_width(lines, measure, measure(node$value_text, "label"), sankey_label_space(style))
}

# Widths of the two outer label columns: their labels' widths while both fit `room`; otherwise a column narrower
# than half keeps its width and the other takes the rest, or each takes half.
sankey_outer_rooms <- function(left, right, room) {
  if (left + right <= room) return(c(left, right))
  if (left <= room / 2) return(c(left, room - left))
  if (right <= room / 2) return(c(room - right, right))
  c(room / 2, room / 2)
}

# Name and value centred above the node, on a surface halo so links behind stay quiet; a wrapped name stacks its
# lines upwards from the node, the value after the last.
sankey_middle_label <- function(node, lines, top, centre, measure, style, rules) {
  size <- style$sizes$label
  base <- style$base
  neutral <- style$neutral
  line <- line_height(style, "label")
  count <- length(lines)
  space <- sankey_label_space(style)
  value <- measure(node$value_text, "label")
  widths <- vapply(lines, measure, numeric(1), role = "label", USE.NAMES = FALSE)
  widths[count] <- if (nzchar(lines[count])) widths[count] + space + value else value
  baseline <- top - rules$label_pad * base - style$descender * size
  first <- baseline - (count - 1) * line
  pad <- rules$halo_pad * base
  half <- max(widths) / 2
  upper <- first - style$cap_height * size - pad
  lower <- baseline + style$descender * size + pad
  shapes <- list(list(kind = "polygon", fill = neutral$surface, role = "halo",
                      points = rbind(c(centre - half - pad, upper), c(centre + half + pad, upper),
                                     c(centre + half + pad, lower), c(centre - half - pad, lower))))
  for (index in seq_len(count)) {
    if (!nzchar(lines[index])) next
    shapes[[length(shapes) + 1]] <- shape_text(centre - widths[index] / 2, first + (index - 1) * line, lines[index],
                                               "label", neutral$ink)
  }
  c(shapes, list(shape_text(centre - widths[count] / 2 + widths[count] - value, baseline, node$value_text, "label",
                            neutral$muted)))
}

sankey_label_shapes <- function(ordered, positions, xs, width, measure, style, rules, lines) {
  gap <- rules$label_gap * style$base
  line <- line_height(style, "label")
  donut <- hl_tokens()$donut
  shapes <- list()
  for (index in seq_along(ordered)) {
    for (node in ordered[[index]]) {
      span <- positions[[index]][[node$name]]
      name <- lines[[index]][[node$name]]
      first <- mean(span) - (length(name) - 1) * line / 2
      segment <- list(name = node$name, share_text = node$value_text)
      shapes <- c(shapes, if (index == 1) {
        label_pair(segment, xs[index] - gap, first, "left", measure, style, donut, name)
      } else if (index == length(ordered)) {
        label_pair(segment, xs[index] + width + gap, first, "right", measure, style, donut, name)
      } else {
        sankey_middle_label(node, name, span[1], xs[index] + width / 2, measure, style, rules)
      })
    }
  }
  shapes
}

sankey_heading_shapes <- function(headings, xs, width, baseline, style) {
  last <- length(xs)
  lapply(seq_along(xs), function(index) {
    x <- if (index == 1) xs[index] + width else if (index == last) xs[index] else xs[index] + width / 2
    align <- if (index == 1) "right" else if (index == last) "left" else "center"
    shape_text(x, baseline, headings[[index]], "label", style$neutral$muted, align)
  })
}

sankey_outer_width <- function(nodes, measure, style, rules) {
  space <- hl_tokens()$donut$label_space * style$sizes$label
  max(vapply(nodes, function(node) measure(node$name, "label") + space + measure(node$value_text, "label"),
             numeric(1))) + rules$label_gap * style$base
}

# Every node's label lines and the x of each column: the outer labels share what the links leave them at
# `min_plot`, the middle labels the space between columns.
sankey_column_lines <- function(spec, box, width, measure, style, rules) {
  nodes <- spec$nodes
  count <- length(nodes)
  gap <- rules$label_gap * style$base
  rooms <- sankey_outer_rooms(sankey_outer_width(nodes[[1]], measure, style, rules),
                              sankey_outer_width(nodes[[count]], measure, style, rules),
                              box[3] - width - rules$min_plot * style$base)
  outer <- list(sankey_node_lines(nodes[[1]], rooms[1] - gap, measure, style),
                sankey_node_lines(nodes[[count]], rooms[2] - gap, measure, style))
  column_width <- function(column, lines) {
    max(vapply(column, function(node) sankey_block_width(node, lines[[node$name]], measure, style), numeric(1))) + gap
  }
  first <- box[1] + column_width(nodes[[1]], outer[[1]])
  last <- box[1] + box[3] - column_width(nodes[[count]], outer[[2]]) - width
  xs <- first + (last - first) * (seq_len(count) - 1) / (count - 1)
  middle <- lapply(nodes[-c(1, count)], function(column) {
    sankey_node_lines(column, (last - first) / (count - 1) - 2 * gap, measure, style)
  })
  list(lines = c(outer[1], middle, outer[2]), xs = xs)
}

# Labels wrap when the links would keep less than `min_plot`; the gap between nodes holds the tallest label, and a
# column with more nodes than the panel holds runs on below it (the figure grows).
sankey_drawing <- function(spec, box, measure, style) {
  rules <- hl_tokens()$sankey
  base <- style$base
  count <- length(spec$nodes)
  line <- line_height(style, "label")
  width <- rules$node_width * base
  columns <- sankey_column_lines(spec, box, width, measure, style, rules)
  counts <- lapply(columns$lines, function(column) vapply(column, length, integer(1)))
  tallest <- max(unlist(counts))
  raised <- max(c(0, unlist(counts[-c(1, count)])))
  gap <- tallest * line + rules$node_gap * base
  top <- box[2] + line + rules$heading_gap * base + raised * line
  most <- max(vapply(spec$nodes, length, integer(1)))
  placed <- sankey_place(spec, top, max(box[2] + box[4] - top, (most - 1) * gap + most * line), gap)
  heading <- baseline_for(box[2] + line / 2, style, "label")
  c(sankey_link_shapes(spec, placed$positions, columns$xs, width, placed$scale, rules),
    sankey_node_shapes(placed$ordered, placed$positions, columns$xs, width),
    sankey_label_shapes(placed$ordered, placed$positions, columns$xs, width, measure, style, rules, columns$lines),
    sankey_heading_shapes(spec$headings, columns$xs, width, heading, style))
}
