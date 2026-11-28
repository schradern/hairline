# Process diagram geometry in pt: lane names at the left, lanes between hairline rules, one column per stage with
# gaps wide enough for the flow labels that start in them, steps as outlined boxes centred in their lane, note
# numbers on the boxes' corners and the notes below each section. Mirrors the Python package's
# charts/process_geometry.py.

# Height of `count` label lines from the first line's cap height to the last baseline. As Python's block().
process_block <- function(count, style) style$cap_height * style$sizes$label + (count - 1) * line_height(style, "label")

# Room a flow label leaves for the note number on its step's corner. As Python's label_offset().
process_label_offset <- function(step, rules, base) if (!is.null(step[["note"]])) rules$marker * base else 0

# Each gap between stages wide enough for the labels of the flows that leave into it, and room to turn. As Python's
# gap_widths().
process_gap_widths <- function(spec, measure, rules, base) {
  gaps <- rep(rules$stage_gap * base, spec$stages - 1)
  for (section in spec$sections) {
    for (flow in section$flows) {
      source <- section$steps[[flow$source + 1]]
      target <- section$steps[[flow$target + 1]]
      if (nzchar(flow$label) && target$stage > source$stage) {
        need <- 2 * rules$label_pad * base + process_label_offset(source, rules, base) +
          measure(flow$label, "label") + rules$turn * base
        gaps[source$stage + 1] <- max(gaps[source$stage + 1], need)
      }
    }
  }
  gaps
}

# The lane names' column and wrapped names, each stage's left edge, the stages' width and each gap's turn. As
# Python's stage_layout().
process_stage_layout <- function(spec, box, measure, rules, base) {
  room <- min(max(vapply(spec$lanes, measure, numeric(1), role = "label")), rules$lane_share * box[3])
  names <- lapply(spec$lanes, fit_lines, room = room, measure = measure, chart = "process", what = "lane name")
  lane_width <- max(vapply(names, widest_line, numeric(1), measure = measure))
  gaps <- process_gap_widths(spec, measure, rules, base)
  start <- box[1] + lane_width + rules$lane_gap * base
  width <- (box[1] + box[3] - start - sum(gaps)) / spec$stages
  if (width < rules$min_stage * base) {
    need <- rules$min_stage * base * spec$stages + start - box[1] + sum(gaps)
    stop(sprintf(paste("hairline: process: %d stages need %.0f pt, but the figure leaves %.0f pt; shorten the flow",
                       "labels or use a wider size"), as.integer(spec$stages), need, box[3]), call. = FALSE)
  }
  lefts <- start + (seq_len(spec$stages) - 1) * width + c(0, cumsum(gaps))
  list(names = names, lefts = lefts, width = width, turns = lefts[-1] - rules$turn * base)
}

# Each step's box and wrapped name, and each lane's top and height: as tall as its tallest box (or name). As
# Python's section_places().
process_section_places <- function(section, layout, top, measure, style, rules) {
  pad <- rules$box_pad * style$base
  lines <- lapply(section$steps, function(step) {
    fit_lines(step$name, layout$width - 2 * pad, measure, "process", "step")
  })
  heights <- vapply(lines, function(names) process_block(length(names), style) + 2 * pad, numeric(1))
  lanes <- vapply(section$steps, `[[`, 0, "lane")
  places <- vector("list", length(section$steps))
  spans <- list()
  for (lane in seq_along(layout$names) - 1) {
    tall <- max(c(process_block(length(layout$names[[lane + 1]]), style) + 2 * pad,
                  process_block(1, style) + 2 * pad, heights[lanes == lane]))
    height <- tall + 2 * rules$lane_pad * style$base
    centre <- top + height / 2
    for (index in which(lanes == lane)) {
      step <- section$steps[[index]]
      left <- layout$lefts[step$stage + 1]
      places[[index]] <- c(step, list(lines = lines[[index]], left = left, right = left + layout$width,
                                      top = centre - tall / 2, bottom = centre + tall / 2,
                                      cx = left + layout$width / 2, cy = centre))
    }
    spans[[length(spans) + 1]] <- c(top, height)
    top <- top + height
  }
  list(places = places, spans = spans)
}

process_centred_lines <- function(lines, x, centre, style, colour, align) {
  first <- centre - process_block(length(lines), style) / 2 + style$cap_height * style$sizes$label
  lapply(seq_along(lines), function(index) {
    shape_text(x, first + (index - 1) * line_height(style, "label"), lines[index], "label", colour, align)
  })
}

# A hairline above each lane and below the last, the lane's name at the left, centred on the lane. As Python's
# lane_shapes().
process_lane_shapes <- function(spans, names, box, style) {
  last <- spans[[length(spans)]]
  edges <- c(vapply(spans, `[`, 0, 1), last[1] + last[2])
  shapes <- lapply(edges, function(y) {
    list(kind = "line", points = rbind(c(box[1], y), c(box[1] + box[3], y)), color = style$neutral$axis,
         width = style$grid, role = "lane_rule")
  })
  for (index in seq_along(spans)) {
    span <- spans[[index]]
    shapes <- c(shapes, lapply(process_centred_lines(names[[index]], box[1], span[1] + span[2] / 2, style,
                                                     style$neutral$muted, "left"), c, part = "lane"))
  }
  shapes
}

# A note number in a filled circle, its digits in the surface colour. As Python's marker().
process_marker <- function(x, y, number, colour, style, rules) {
  radius <- rules$marker * style$base
  angles <- 2 * pi * (seq_len(rules$marker_steps) - 1) / rules$marker_steps
  list(list(kind = "polygon", points = cbind(x + radius * cos(angles), y + radius * sin(angles)), fill = colour,
            role = "marker"),
       c(shape_text(x, y + style$cap_height * style$sizes$label / 2, as.character(number), "label",
                    style$neutral$surface, "center", hl_tokens()$type$key_weight), part = "marker"))
}

# The box, outlined in the axis colour, in the accent when highlighted, dashed when tentative; its tooltip. As
# Python's step_box().
process_step_box <- function(place, style, rules, accent) {
  corners <- rbind(c(place$left, place$top), c(place$right, place$top), c(place$right, place$bottom),
                   c(place$left, place$bottom))
  shape <- list(kind = "polygon", points = corners, fill = style$neutral$surface, role = "step")
  if (identical(place$status, "highlight")) {
    shape <- c(shape, list(edge = accent, edge_width = rules$highlight_width * style$base))
  } else if (is.null(place$status)) {
    shape <- c(shape, list(edge = style$neutral$axis, edge_width = style$axis_width))
  }
  parts <- c(place$name, place$lane_name, place$note_text)
  shapes <- list(c(shape, list(series = place$name, tip = paste(parts[nzchar(parts)], collapse = "\n"),
                               tip_at = c((place$left + place$right) / 2, place$top), hover_only = TRUE)))
  if (identical(place$status, "tentative")) {
    shapes[[2]] <- list(kind = "line", points = rbind(corners, corners[1, ]), color = style$neutral$faint,
                        width = style$axis_width, dash = unlist(rules$dash), role = "step_edge")
  }
  shapes
}

process_step_shapes <- function(places, style, rules, accent) {
  shapes <- list()
  for (place in places) {
    colour <- if (identical(place$status, "tentative")) style$neutral$muted else style$neutral$ink
    shapes <- c(shapes, process_step_box(place, style, rules, accent),
                lapply(process_centred_lines(place$lines, place$cx, place$cy, style, colour, "center"), c,
                       part = "step"))
    if (!is.null(place[["note"]])) {
      shapes <- c(shapes, process_marker(place$right, place$top, place[["note"]],
                                         if (identical(place$status, "highlight")) accent else style$neutral$ink,
                                         style, rules))
    }
  }
  shapes
}

# The notes one under another, each after its number; the bottom of the last. As Python's note_shapes().
process_note_shapes <- function(notes, top, box, measure, style, rules, accent) {
  base <- style$base
  line <- line_height(style, "label")
  cap <- style$cap_height * style$sizes$label
  indent <- rules$note_indent * base
  shapes <- list()
  for (note in notes) {
    lines <- fit_lines(note$text, box[3] - indent, measure, "process", "note")
    colour <- if (identical(note$status, "highlight")) accent else style$neutral$ink
    shapes <- c(shapes, process_marker(box[1] + rules$marker * base, top + cap / 2, note$number, colour, style, rules),
                lapply(seq_along(lines), function(index) {
                  c(shape_text(box[1] + indent, top + cap + (index - 1) * line, lines[index], "label",
                               style$neutral$muted), part = "note")
                }))
    top <- top + cap + (length(lines) - 1) * line + rules$note_gap * base + line - cap
  }
  list(shapes = shapes, bottom = top)
}

process_drawing <- function(spec, box, measure, style) {
  rules <- hl_tokens()$process
  base <- style$base
  layout <- process_stage_layout(spec, box, measure, rules, base)
  shapes <- list()
  top <- box[2]
  for (index in seq_along(spec$sections)) {
    section <- spec$sections[[index]]
    if (index > 1) top <- top + rules$section_gap * base
    if (!is.null(section$name)) {
      baseline <- top + style$cap_height * style$sizes$panel
      shapes[[length(shapes) + 1]] <- c(shape_text(box[1], baseline, section$name, "panel", style$neutral$ink),
                                        part = "section")
      top <- baseline + rules$heading_gap * base
    }
    section$steps <- lapply(section$steps, function(step) c(step, list(lane_name = spec$lanes[step$lane + 1])))
    placed <- process_section_places(section, layout, top, measure, style, rules)
    places <- placed$places
    cells <- vapply(places, function(place) paste(place$lane, place$stage), "")
    where <- if (is.null(section$name)) "" else sprintf(" in section '%s'", section$name)
    shapes <- c(shapes, process_lane_shapes(placed$spans, layout$names, box, style))
    for (flow in section$flows) {
      shapes <- c(shapes, process_flow_shapes(flow, places, cells, layout$turns, style, rules, spec$accent, where))
    }
    shapes <- c(shapes, process_step_shapes(places, style, rules, spec$accent))
    for (flow in section$flows) {
      source <- places[[flow$source + 1]]
      shapes <- c(shapes, process_flow_label(flow, source, places[[flow$target + 1]], measure, style, rules,
                                             process_label_offset(source, rules, base)))
    }
    last <- placed$spans[[length(placed$spans)]]
    top <- last[1] + last[2]
    if (length(section$notes)) {
      notes <- process_note_shapes(section$notes, top + rules$notes_gap * base, box, measure, style, rules,
                                   spec$accent)
      shapes <- c(shapes, notes$shapes)
      top <- notes$bottom
    }
  }
  shapes
}
