# Chord diagram, mirroring the Python chord(): groups as arcs on a ring sized by their total, ribbons through the
# centre joining each pair with the pair's value at both ends, labels outside with leader lines.

chord_spec <- function(data, source, target, value = NULL, order = NULL, colors = NULL) {
  counted <- with_counts(data, value)
  data <- counted$data
  value <- counted$value
  flows <- flow_rows(data, source, target, value, "chord", order)
  data <- flows$rows
  names <- flows$names
  keys <- character()
  totals <- numeric()
  ends <- list()
  for (row in seq_len(nrow(data))) {
    first <- as.character(data[[source]][row])
    second <- as.character(data[[target]][row])
    amount <- data[[value]][row]
    if (first == second) next
    pair <- if (match(first, names) <= match(second, names)) c(first, second) else c(second, first)
    key <- combination_key(pair[1], pair[2])
    if (!key %in% keys) {
      keys <- c(keys, key)
      totals[[key]] <- 0
      ends[[key]] <- pair
    }
    totals[[key]] <- totals[[key]] + amount
  }
  links <- lapply(keys[totals[keys] > 0], function(key) {
    list(source = ends[[key]][1], target = ends[[key]][2], value = totals[[key]])
  })
  palette <- colours_for(names, colors)
  flows <- vapply(names, function(name) {
    sum(vapply(links, function(link) if (name %in% c(link$source, link$target)) link$value else 0, numeric(1)))
  }, numeric(1))
  digits <- auto_digits(vapply(links, `[[`, numeric(1), "value"))
  nodes <- lapply(names[flows > 0], function(name) {
    list(name = name, value = flows[[name]], value_text = hl_format_number(flows[[name]], digits),
         color = palette[[name]])
  })
  list(nodes = nodes, links = links)
}

chord_spans <- function(spec, rules) {
  values <- vapply(spec$nodes, function(node) as.numeric(node$value), numeric(1))
  available <- 360 - rules$gap_degrees * length(values)
  spans <- list()
  start <- 90 - rules$gap_degrees / 2
  for (value in values) {
    end <- start - available * value / sum(values)
    spans[[length(spans) + 1]] <- c(start, end)
    start <- end - rules$gap_degrees
  }
  spans
}

chord_link_ends <- function(spec, spans) {
  names <- vapply(spec$nodes, `[[`, character(1), "name")
  ends <- list()
  for (index in seq_along(names)) {
    touching <- which(vapply(spec$links, function(link) names[index] %in% c(link$source, link$target), logical(1)))
    partners <- vapply(touching, function(position) {
      link <- spec$links[[position]]
      other <- if (link$source == names[index]) link$target else link$source
      (match(other, names) - index) %% length(names)
    }, numeric(1))
    cursor <- spans[[index]][1]
    for (position in touching[order(partners, touching)]) {
      width <- (spans[[index]][1] - spans[[index]][2]) * as.numeric(spec$links[[position]]$value) /
        as.numeric(spec$nodes[[index]]$value)
      ends[[paste(position, index)]] <- c(cursor, cursor - width)
      cursor <- cursor - width
    }
  }
  ends
}

chord_bend <- function(start, end, centre, count) {
  t <- (1:(count - 1)) / count
  cbind((1 - t)^2 * start[1] + 2 * (1 - t) * t * centre[1] + t^2 * end[1],
        (1 - t)^2 * start[2] + 2 * (1 - t) * t * centre[2] + t^2 * end[2])
}

chord_ribbon <- function(first, second, cx, cy, radius, step) {
  one <- donut_arc(cx, cy, radius, first[1], first[2], step)
  two <- donut_arc(cx, cy, radius, second[1], second[2], step)
  rbind(one, chord_bend(one[nrow(one), ], two[1, ], c(cx, cy), 16), two,
        chord_bend(two[nrow(two), ], one[1, ], c(cx, cy), 16))
}

chord_drawing <- function(spec, box, measure, style) {
  rules <- hl_tokens()$chord
  donut <- hl_tokens()$donut
  segments <- lapply(spec$nodes, function(node) list(name = node$name, share_text = node$value_text))
  side <- outside_width(segments, measure, style, donut)
  fitted <- min(box[4] / 2 - line_height(style, "label") / 2, (box[3] - 2 * side) / 2)
  radius <- max(fitted, donut$min_radius * style$base)
  cx <- box[1] + box[3] / 2
  cy <- box[2] + box[4] / 2
  inner <- radius * (1 - rules$ring)
  spans <- chord_spans(spec, rules)
  ends <- chord_link_ends(spec, spans)
  names <- vapply(spec$nodes, `[[`, character(1), "name")
  shapes <- list()
  for (position in seq_along(spec$links)) {
    link <- spec$links[[position]]
    first <- match(link$source, names)
    second <- match(link$target, names)
    pair <- paste(link$source, "\u2013", link$target)
    ribbon <- list(kind = "polygon", role = "ribbon", fill = spec$nodes[[first]]$color, alpha = rules$ribbon_opacity,
                   points = chord_ribbon(ends[[paste(position, first)]], ends[[paste(position, second)]], cx, cy,
                                         inner - rules$ribbon_gap, rules$arc_step))
    shapes[[length(shapes) + 1]] <- tagged_shape(ribbon, pair, paste0(pair, ": ", amount_text(link$value)))
  }
  for (index in seq_along(spec$nodes)) {
    span <- spans[[index]]
    node <- list(kind = "polygon", role = "node", name = names[index], span = span[1] - span[2],
                 fill = spec$nodes[[index]]$color,
                 points = rbind(donut_arc(cx, cy, radius, span[1], span[2], rules$arc_step),
                                donut_arc(cx, cy, inner, span[2], span[1], rules$arc_step)))
    shapes[[length(shapes) + 1]] <- tagged_shape(node, names[index],
                                                 paste0(names[index], ": ", spec$nodes[[index]]$value_text))
  }
  c(shapes, outside_labels(segments, cx, cy, radius, box, measure, style, donut, spans,
                           outside_lines(segments, box, radius, measure, style, donut, "chord")))
}

#' Chord diagram
#'
#' Groups as arcs on a ring, each sized by its total, and ribbons through the
#' centre joining each pair (both directions combined), as wide as the pair's
#' value at both ends; without `value` each row counts once.
#'
#' @param data A data frame, one row per exchange (or per pair with a value).
#' @param source,target Columns naming the two groups.
#' @param value Column with the amounts; `NULL` counts rows.
#' @param title,subtitle,caption Frame texts; the title defaults to the columns.
#' @param order Group order around the ring, clockwise from the top.
#' @param colors Named colours for this chart only; they override the colour set for the number of groups.
#' @return A ggplot with the hairline frame.
#' @examples
#' transfers <- data.frame(origin = c("ICU", "Ward", "ICU", "Step-down", "Ward"),
#'                         destination = c("Ward", "ICU", "Step-down", "Ward", "Step-down"))
#' hl_chord(transfers, "origin", "destination")
#' @export
hl_chord <- function(data, source, target, value = NULL, title = NULL, subtitle = NULL, caption = NULL, order = NULL,
                     colors = NULL) {
  spec <- chord_spec(data, source, target, value, order, colors)
  label <- if (is.null(value)) "Count" else humanise(value)
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title %||% paste(label, "between", gsub("_", " ", source), "and", gsub("_", " ", target)),
                  subtitle = subtitle, caption = caption, x = NULL, y = NULL) + theme_hairline(axes = FALSE)
  plot@meta$hairline_drawing <- function(box, measure, style) chord_drawing(spec, box, measure, style)
  plot@meta$hairline_fit_height <- "grow"
  plot
}
