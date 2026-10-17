# Donut labels: names and shares outside with leader lines, inside the rings, the centre total and the key.

label_pair <- function(segment, x, y, side, measure, style, rules) {
  space <- rules$label_space * style$sizes$label
  baseline <- baseline_for(y, style, "label")
  neutral <- style$neutral
  if (side == "right") {
    width <- measure(segment$name, "label")
    return(list(shape_text(x, baseline, segment$name, "label", neutral$ink),
                shape_text(x + width + space, baseline, segment$share_text, "label", neutral$muted)))
  }
  width <- measure(segment$share_text, "label")
  list(shape_text(x - width - space, baseline, segment$name, "label", neutral$ink, "right"),
       shape_text(x, baseline, segment$share_text, "label", neutral$muted, "right"))
}

outside_width <- function(ring, measure, style, rules) {
  space <- rules$label_space * style$sizes$label
  widths <- vapply(ring, function(segment) {
    measure(segment$name, "label") + space + measure(segment$share_text, "label")
  }, numeric(1))
  (rules$leader_elbow + rules$leader_run + rules$label_gap) * style$base + max(c(0, widths))
}

leader_entries <- function(ring, cx, cy, radius, style, rules) {
  spans <- ring_spans(ring)
  lapply(seq_along(ring), function(index) {
    middle <- mean(spans[[index]])
    list(segment = ring[[index]], side = if (cos(middle * pi / 180) >= -1e-9) "right" else "left",
         anchor = donut_point(cx, cy, radius + rules$leader_offset * style$base, middle),
         knee = donut_point(cx, cy, radius + rules$leader_elbow * style$base, middle))
  })
}

outside_labels <- function(ring, cx, cy, radius, box, measure, style, rules) {
  line <- line_height(style, "label")
  reach <- radius + (rules$leader_elbow + rules$leader_run) * style$base
  entries <- leader_entries(ring, cx, cy, radius, style, rules)
  shapes <- list()
  for (side in c("left", "right")) {
    direction <- if (side == "left") -1 else 1
    group <- Filter(function(entry) entry$side == side, entries)
    ys <- spread_labels(vapply(group, function(entry) entry$knee[2], numeric(1)), line, box[2] + line / 2,
                        box[2] + box[4] - line / 2)
    for (index in seq_along(group)) {
      entry <- group[[index]]
      end_x <- cx + direction * reach
      points <- rbind(entry$anchor, c(entry$knee[1], ys[index]), c(end_x, ys[index]))
      shapes[[length(shapes) + 1]] <- list(kind = "line", points = unname(points), color = style$neutral$axis,
                                           width = style$leader_width)
      shapes <- c(shapes, label_pair(entry$segment, end_x + direction * rules$label_gap * style$base, ys[index],
                                     side, measure, style, rules))
    }
  }
  shapes
}

centre_total <- function(total, label, cx, cy, style) {
  if (is.null(total)) return(list())
  caption_line <- line_height(style, "caption")
  value_baseline <- baseline_for(cy, style, "panel") - if (is.null(label)) 0 else caption_line / 2
  shapes <- list(shape_text(cx, value_baseline, total, "panel", style$neutral$ink, "center"))
  if (!is.null(label)) {
    shapes[[2]] <- shape_text(cx, value_baseline + caption_line, label, "caption", style$neutral$muted, "center")
  }
  shapes
}
