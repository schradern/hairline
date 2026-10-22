# Forest plot axis, pooled row and the entry point forest_drawing().

# The favours labels either side of the null line, each wrapped into the room between it and the panel's edge,
# lines running down.
forest_favours_shapes <- function(spec, null, baseline, box, measure, style, rules) {
  gap <- rules$favours_gap * style$base
  line <- line_height(style, "label")
  sides <- list(list(label = spec$favours[[1]], x = null - gap, room = null - gap - box[1], align = "right"),
                list(label = spec$favours[[2]], x = null + gap, room = box[1] + box[3] - null - gap, align = "left"))
  shapes <- list()
  for (side in sides) {
    lines <- fit_lines(side$label, side$room, measure, "forest", "the favours label")
    for (index in seq_along(lines)) {
      shapes[[length(shapes) + 1]] <- c(shape_text(side$x, baseline + (index - 1) * line, lines[index], "label",
                                                   style$neutral$muted, side$align), part = "favours")
    }
  }
  shapes
}

# Axis line and ticks; with `favours` (which needs `box` and `measure`), the labels either side of null.
forest_axis_shapes <- function(spec, scale, plot, y, style, rules, box = NULL, measure = NULL) {
  base <- style$base
  muted <- style$neutral$muted
  shapes <- list(list(kind = "line", points = rbind(c(plot[1], y), c(plot[2], y)), color = style$neutral$axis,
                      width = style$axis_width))
  tick_baseline <- y + rules$axis_gap * base + style$cap_height * style$sizes$label
  for (index in seq_along(spec$axis$breaks)) {
    tick <- shape_text(scale(spec$axis$breaks[[index]]), tick_baseline, spec$axis$labels[[index]], "label", muted,
                       "center")
    shapes[[length(shapes) + 1]] <- c(tick, part = "tick")
  }
  if (!is.null(spec$favours) && !is.null(spec$null)) {
    baseline <- tick_baseline + line_height(style, "label") + rules$favours_gap * base
    shapes <- c(shapes, forest_favours_shapes(spec, scale(spec$null), baseline, box, measure, style, rules))
  }
  shapes
}

forest_pooled_shapes <- function(spec, columns, top, bottom, pitch, centre, scale, style, rules) {
  pooled <- c(spec$pooled, list(study = spec$pooled$label, cells = as.list(rep("", length(spec$columns))),
                                bold = TRUE))
  divider <- top + pitch * (length(spec$rows) + rules$pooled_gap / 2)
  x <- scale(pooled$estimate)
  half <- rules$max_square * style$base / 2
  diamond <- list(kind = "polygon", fill = style$neutral$ink, role = "diamond",
                  points = rbind(c(scale(pooled$low), centre), c(x, centre - half), c(scale(pooled$high), centre),
                                 c(x, centre + half)))
  c(list(forest_rule(columns$study, columns$right, divider, style),
         list(kind = "line", points = rbind(c(x, top), c(x, bottom)), color = style$neutral$faint,
              width = style$leader_width, dash = rules$pooled_dash),
         diamond),
    forest_table_texts(spec, columns, baseline_for(centre, style, "label"), pooled, style))
}

forest_drawing <- function(spec, box, measure, style) {
  rules <- hl_tokens()$forest
  base <- style$base
  size <- style$sizes$label
  line <- line_height(style, "label")
  columns <- forest_columns(spec, box, measure, rules, base)
  columns$lead <- if (columns$under) line else 0
  scale <- forest_scale(spec$axis, isTRUE(spec$ratio), columns$plot[1], columns$plot[2])
  heading <- box[2] + style$cap_height * size
  top <- heading + line - style$cap_height * size + rules$rule_gap * base + columns$lead
  count <- length(spec$rows) + if (is.null(spec$pooled)) 0 else 1 + rules$pooled_gap
  # Rows keep their pitch; the figure's height follows them (hairline_fit_height), so many rows never overlap. A row
  # whose columns sit under it is a line taller, and its interval stays on its first line.
  line_pitch <- rules$row_pitch * line
  pitch <- line_pitch + columns$lead
  bottom <- top + pitch * count
  sides <- if (identical(spec$marker, "dot")) rep(dot_size(style), length(spec$rows)) else
    forest_sides(spec, rules, base)
  shapes <- c(forest_table_texts(spec, columns, heading, NULL, style),
              list(forest_rule(columns$study, columns$right, top, style)))
  for (index in seq_along(spec$rows)) {
    centre <- top + pitch * (index - 1) + line_pitch / 2
    shapes <- c(shapes, forest_table_texts(spec, columns, baseline_for(centre, style, "label"), spec$rows[[index]],
                                           style),
                forest_marks(spec$rows[[index]], centre, scale, columns$plot, sides[index], spec, style))
  }
  if (!is.null(spec$null)) {
    null <- scale(spec$null)
    shapes[[length(shapes) + 1]] <- list(kind = "line", points = rbind(c(null, top), c(null, bottom)),
                                         color = style$neutral$muted, width = style$leader_width, part = "null")
  }
  if (!is.null(spec$pooled)) {
    centre <- top + pitch * length(spec$rows) + line_pitch / 2 + rules$pooled_gap * pitch
    shapes <- c(shapes, forest_pooled_shapes(spec, columns, top, bottom, pitch, centre, scale, style, rules))
  }
  c(shapes, forest_axis_shapes(spec, scale, columns$plot, bottom + rules$axis_gap * base, style, rules, box,
                               measure))
}
