# Donut labels: names and shares outside with leader lines, inside the rings, the centre total and the key.

# Name in ink, share in muted, aligned away from the donut. A wrapped name takes `lines`, the first centred on `y`;
# the share follows the last, or stands alone after an empty last line.
label_pair <- function(segment, x, y, side, measure, style, rules, lines = NULL) {
  lines <- lines %||% segment$name
  count <- length(lines)
  line <- line_height(style, "label")
  space <- rules$label_space * style$sizes$label
  baseline <- baseline_for(y + (count - 1) * line, style, "label")
  neutral <- style$neutral
  align <- if (side == "right") "left" else "right"
  shapes <- lapply(seq_len(count - 1), function(index) {
    shape_text(x, baseline_for(y + (index - 1) * line, style, "label"), lines[index], "label", neutral$ink, align)
  })
  last <- lines[count]
  if (!nzchar(last)) return(c(shapes, list(shape_text(x, baseline, segment$share_text, "label", neutral$muted,
                                                      align))))
  if (side == "right") {
    width <- measure(last, "label")
    return(c(shapes, list(shape_text(x, baseline, last, "label", neutral$ink),
                          shape_text(x + width + space, baseline, segment$share_text, "label", neutral$muted))))
  }
  width <- measure(segment$share_text, "label")
  c(shapes, list(shape_text(x - width - space, baseline, last, "label", neutral$ink, "right"),
                 shape_text(x, baseline, segment$share_text, "label", neutral$muted, "right")))
}

outside_width <- function(ring, measure, style, rules) {
  space <- rules$label_space * style$sizes$label
  widths <- vapply(ring, function(segment) {
    measure(segment$name, "label") + space + measure(segment$share_text, "label")
  }, numeric(1))
  (rules$leader_elbow + rules$leader_run + rules$label_gap) * style$base + max(c(0, widths))
}

# Each label's lines: one while the labels fit beside the ring, wrapped into the room beside a ring of the minimum
# radius otherwise.
outside_lines <- function(ring, box, radius, measure, style, rules, chart) {
  room <- box[3] / 2 - radius - (rules$leader_elbow + rules$leader_run + rules$label_gap) * style$base
  space <- rules$label_space * style$sizes$label
  lapply(ring, function(segment) {
    fit_lines(segment$name, room, measure, chart, "the label", measure(segment$share_text, "label"), space)
  })
}

leader_entries <- function(ring, cx, cy, radius, style, rules, spans = NULL) {
  spans <- spans %||% ring_spans(ring)
  lapply(seq_along(ring), function(index) {
    middle <- mean(spans[[index]])
    list(segment = ring[[index]], side = if (cos(middle * pi / 180) >= -1e-9) "right" else "left",
         anchor = donut_point(cx, cy, radius + rules$leader_offset * style$base, middle),
         knee = donut_point(cx, cy, radius + rules$leader_elbow * style$base, middle))
  })
}

# Labels beside the ring on leader lines that meet their first line; labels taller than the panel run on below it
# (the figure grows to hold them).
outside_labels <- function(ring, cx, cy, radius, box, measure, style, rules, spans = NULL, lines = NULL) {
  line <- line_height(style, "label")
  reach <- radius + (rules$leader_elbow + rules$leader_run) * style$base
  entries <- leader_entries(ring, cx, cy, radius, style, rules, spans)
  lines <- lines %||% lapply(ring, `[[`, "name")
  for (index in seq_along(entries)) entries[[index]]$lines <- lines[[index]]
  shapes <- list()
  for (side in c("left", "right")) {
    direction <- if (side == "left") -1 else 1
    group <- Filter(function(entry) entry$side == side, entries)
    counts <- vapply(group, function(entry) length(entry$lines), numeric(1))
    lifts <- (counts - 1) * line / 2
    centres <- spread_blocks(vapply(group, function(entry) entry$knee[2], numeric(1)) + lifts, counts * line,
                             box[2], box[2] + box[4])
    for (index in seq_along(group)) {
      entry <- group[[index]]
      y <- centres[index] - lifts[index]
      end_x <- cx + direction * reach
      points <- rbind(entry$anchor, c(entry$knee[1], y), c(end_x, y))
      shapes[[length(shapes) + 1]] <- list(kind = "line", points = unname(points), color = style$neutral$axis,
                                           width = style$leader_width)
      shapes <- c(shapes, label_pair(entry$segment, end_x + direction * rules$label_gap * style$base, y, side,
                                     measure, style, rules, entry$lines))
    }
  }
  shapes
}

# The total's label in as few lines as the hole allows: the block of value and lines fits inside the circle.
total_lines <- function(label, hole, measure, style) {
  panel <- line_height(style, "panel")
  caption <- line_height(style, "caption")
  count <- 1
  while ((panel + count * caption) / 2 < hole) {
    room <- 2 * sqrt(hole^2 - ((panel + count * caption) / 2)^2)
    lines <- wrap_words(label, room + wrap_tolerance, measure, "caption")
    if (widest_line(lines, measure, "caption") > room + wrap_tolerance) break
    if (length(lines) <= count) return(lines)
    count <- count + 1
  }
  words <- strsplit(trimws(label), "\\s+")[[1]]
  widths <- vapply(words, measure, numeric(1), role = "caption")
  stop(sprintf(paste("hairline: donut: total_label '%s' does not fit the hole, %.0f pt across ('%s' alone needs %.0f",
                     "pt). Shorten it, leave it out, or use a wider size"), label, 2 * hole,
               words[which.max(widths)], max(widths)), call. = FALSE)
}

centre_total <- function(total, label, cx, cy, style, lines = NULL) {
  if (is.null(total)) return(list())
  caption_line <- line_height(style, "caption")
  lines <- lines %||% if (!is.null(label) && nzchar(label)) label else character()
  value_baseline <- baseline_for(cy, style, "panel") - length(lines) * caption_line / 2
  shapes <- list(shape_text(cx, value_baseline, total, "panel", style$neutral$ink, "center"))
  for (index in seq_along(lines)) {
    shapes[[index + 1]] <- shape_text(cx, value_baseline + index * caption_line, lines[index], "caption",
                                      style$neutral$muted, "center")
  }
  shapes
}
