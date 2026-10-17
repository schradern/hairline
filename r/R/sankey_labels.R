# Sankey nodes, labels, headings and the entry point sankey_drawing().

sankey_node_shapes <- function(ordered, positions, xs, width) {
  shapes <- list()
  for (index in seq_along(ordered)) {
    for (node in ordered[[index]]) {
      span <- positions[[index]][[node$name]]
      x <- xs[index]
      shapes[[length(shapes) + 1]] <- list(kind = "polygon", fill = node$color, role = "node", name = node$name,
                                           points = rbind(c(x, span[1]), c(x + width, span[1]),
                                                          c(x + width, span[2]), c(x, span[2])))
    }
  }
  shapes
}

sankey_middle_label <- function(node, top, centre, measure, style, rules) {
  size <- style$sizes$label
  base <- style$base
  neutral <- style$neutral
  space <- hl_tokens()$donut$label_space * size
  name <- measure(node$name, "label")
  value <- measure(node$value_text, "label")
  start <- centre - (name + space + value) / 2
  end <- centre + (name + space + value) / 2
  baseline <- top - rules$label_pad * base - style$descender * size
  pad <- rules$halo_pad * base
  upper <- baseline - style$cap_height * size - pad
  lower <- baseline + style$descender * size + pad
  list(list(kind = "polygon", fill = neutral$surface, role = "halo",
            points = rbind(c(start - pad, upper), c(end + pad, upper), c(end + pad, lower), c(start - pad, lower))),
       shape_text(start, baseline, node$name, "label", neutral$ink),
       shape_text(start + name + space, baseline, node$value_text, "label", neutral$muted))
}

sankey_label_shapes <- function(ordered, positions, xs, width, measure, style, rules) {
  gap <- rules$label_gap * style$base
  donut <- hl_tokens()$donut
  shapes <- list()
  for (index in seq_along(ordered)) {
    for (node in ordered[[index]]) {
      span <- positions[[index]][[node$name]]
      segment <- list(name = node$name, share_text = node$value_text)
      shapes <- c(shapes, if (index == 1) {
        label_pair(segment, xs[index] - gap, mean(span), "left", measure, style, donut)
      } else if (index == length(ordered)) {
        label_pair(segment, xs[index] + width + gap, mean(span), "right", measure, style, donut)
      } else {
        sankey_middle_label(node, span[1], xs[index] + width / 2, measure, style, rules)
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
    shape_text(x, baseline, headings[[index]], "panel", style$neutral$ink, align)
  })
}

sankey_outer_width <- function(nodes, measure, style, rules) {
  space <- hl_tokens()$donut$label_space * style$sizes$label
  max(vapply(nodes, function(node) measure(node$name, "label") + space + measure(node$value_text, "label"),
             numeric(1))) + rules$label_gap * style$base
}

sankey_drawing <- function(spec, box, measure, style) {
  rules <- hl_tokens()$sankey
  base <- style$base
  count <- length(spec$nodes)
  line <- line_height(style, "label")
  width <- rules$node_width * base
  first <- box[1] + sankey_outer_width(spec$nodes[[1]], measure, style, rules)
  last <- box[1] + box[3] - sankey_outer_width(spec$nodes[[count]], measure, style, rules) - width
  xs <- first + (last - first) * (seq_len(count) - 1) / (count - 1)
  top <- box[2] + line_height(style, "panel") + rules$heading_gap * base + if (count > 2) line else 0
  placed <- sankey_place(spec, top, box[2] + box[4] - top, line + rules$node_gap * base)
  heading <- baseline_for(box[2] + line_height(style, "panel") / 2, style, "panel")
  c(sankey_link_shapes(spec, placed$positions, xs, width, placed$scale, rules),
    sankey_node_shapes(placed$ordered, placed$positions, xs, width),
    sankey_label_shapes(placed$ordered, placed$positions, xs, width, measure, style, rules),
    sankey_heading_shapes(spec$headings, xs, width, heading, style))
}
