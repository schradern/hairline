# PRISMA flow geometry in pt, the same algorithm as the Python package's prisma_geometry.

wrap_lines <- function(paragraphs, width, measure) {
  lines <- character()
  for (paragraph in unlist(paragraphs)) {
    current <- ""
    for (word in strsplit(paragraph, " ", fixed = TRUE)[[1]]) {
      if (!nzchar(word)) next
      candidate <- if (nzchar(current)) paste(current, word) else word
      if (nzchar(current) && measure(candidate, "label") > width) {
        lines <- c(lines, current)
        current <- word
      } else {
        current <- candidate
      }
    }
    lines <- c(lines, current)
  }
  lines
}

flow_rectangle <- function(left, top, width, height) {
  rbind(c(left, top), c(left + width, top), c(left + width, top + height), c(left, top + height))
}

flow_arrow <- function(start, end, style, rules) {
  size <- rules$arrow_head * style$base
  colour <- style$neutral$faint
  if (start[1] == end[1]) {
    head <- rbind(end, c(end[1] - size / 2, end[2] - size), c(end[1] + size / 2, end[2] - size))
    stop_at <- c(end[1], end[2] - size)
  } else {
    head <- rbind(end, c(end[1] - size, end[2] - size / 2), c(end[1] - size, end[2] + size / 2))
    stop_at <- c(end[1] - size, end[2])
  }
  list(list(kind = "line", points = rbind(start, stop_at), color = colour, width = style$leader_width, role = "arrow"),
       list(kind = "polygon", points = unname(head), fill = colour, role = "arrow_head"))
}

flow_box_texts <- function(lines, left, top, style, pad) {
  size <- style$sizes$label
  line <- line_height(style, "label")
  lapply(seq_along(lines), function(index) {
    c(shape_text(left + pad, top + pad + style$cap_height * size + (index - 1) * line, lines[index], "label",
                 style$neutral$ink), part = "box_text")
  })
}

prisma_phase_shapes <- function(spec, places, left, style, rules) {
  size <- style$sizes$label
  base <- style$base
  text_x <- left + style$cap_height * size
  bracket_x <- left + line_height(style, "label") + rules$bracket_gap * base
  tick <- rules$bracket_tick * base
  shapes <- list()
  for (phase in spec$phases) {
    top <- places[[phase[[2]] + 1]][1]
    last <- places[[phase[[3]] + 1]]
    bottom <- last[1] + last[2]
    shapes[[length(shapes) + 1]] <- list(kind = "line", color = style$neutral$axis, width = style$leader_width,
                                         points = rbind(c(bracket_x + tick, top), c(bracket_x, top),
                                                        c(bracket_x, bottom), c(bracket_x + tick, bottom)))
    shapes[[length(shapes) + 1]] <- c(shape_text(text_x, (top + bottom) / 2, phase[[1]], "label", style$neutral$muted,
                                                 "center"), rotation = 90, part = "phase")
  }
  shapes
}

prisma_drawing <- function(spec, box, measure, style) {
  rules <- hl_tokens()$prisma
  base <- style$base
  line <- line_height(style, "label")
  pad <- rules$box_pad * base
  gap <- rules$column_gap * base
  phase_width <- line + rules$bracket_gap * base + rules$bracket_tick * base + gap / 2
  main_left <- box[1] + phase_width
  main_width <- (box[3] - phase_width - gap) * rules$main_share
  side_left <- main_left + main_width + gap
  side_width <- box[1] + box[3] - side_left
  shapes <- list()
  places <- list()
  top <- box[2]
  for (row in spec$rows) {
    main <- wrap_lines(row$main, main_width - 2 * pad, measure)
    side <- if (length(row$exclusion)) wrap_lines(row$exclusion, side_width - 2 * pad, measure) else character()
    height <- max(length(main), length(side)) * line + 2 * pad
    shapes <- c(shapes, list(list(kind = "polygon", points = flow_rectangle(main_left, top, main_width, height),
                                  fill = style$neutral$surface, edge = style$neutral$axis,
                                  edge_width = style$axis_width, role = "main")),
                flow_box_texts(main, main_left, top, style, pad))
    if (length(side)) {
      shapes <- c(shapes, list(list(kind = "polygon", points = flow_rectangle(side_left, top, side_width, height),
                                    fill = style$neutral$band, role = "exclusion")),
                  flow_box_texts(side, side_left, top, style, pad),
                  flow_arrow(c(main_left + main_width, top + height / 2), c(side_left, top + height / 2), style, rules))
    }
    if (length(places)) {
      previous <- places[[length(places)]]
      centre <- main_left + main_width / 2
      shapes <- c(shapes, flow_arrow(c(centre, previous[1] + previous[2]), c(centre, top), style, rules))
    }
    places[[length(places) + 1]] <- c(top, height)
    top <- top + height + rules$row_gap * base
  }
  c(shapes, prisma_phase_shapes(spec, places, box[1], style, rules))
}

#' PRISMA 2020 flow diagram
#'
#' Identified, screened, sought, assessed and included records with the
#' exclusions beside them, phases as brackets on the left. Counts that do not
#' add up give a warning.
#'
#' @param counts Named list: identified (and registers), duplicates, automation, other_removed, screened,
#'   excluded, sought, not_retrieved, assessed, excluded_reasons (named numbers), included, reports.
#' @param title,subtitle,caption Frame texts.
#' @return A ggplot with the hairline frame.
#' @examples
#' hl_prisma(list(identified = 1240, duplicates = 260, screened = 980, excluded = 860, sought = 120,
#'                not_retrieved = 10, assessed = 110, excluded_reasons = c("Wrong population" = 92),
#'                included = 18))
#' @export
hl_prisma <- function(counts, title = NULL, subtitle = NULL, caption = NULL) {
  spec <- prisma_spec(counts)
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title %||% "Study selection", subtitle = subtitle, caption = caption, x = NULL, y = NULL) +
    theme_hairline(axes = FALSE)
  plot@meta$hairline_drawing <- function(box, measure, style) prisma_drawing(spec, box, measure, style)
  plot@meta$hairline_fit_height <- TRUE
  plot
}
