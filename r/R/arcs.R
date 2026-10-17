# Arc diagram, mirroring the Python arcs(): nodes on a baseline, half-ellipse arcs above whose
# width follows the value, labels under the nodes (upright when crowded), a width key at the top.

arcs_spec <- function(data, source, target, value = NULL, order = NULL) {
  counted <- with_counts(data, value)
  data <- counted$data
  value <- counted$value
  check_columns(data, c(source, target, value))
  names <- order %||% unique(as.vector(rbind(as.character(data[[source]]), as.character(data[[target]]))))
  keys <- paste(data[[source]], data[[target]], sep = "\r")
  totals <- tapply(data[[value]], factor(keys, levels = unique(keys)), sum)
  links <- list()
  for (key in names(totals)) {
    pair <- strsplit(key, "\r", fixed = TRUE)[[1]]
    if (pair[1] == pair[2] || totals[[key]] <= 0) next
    links[[length(links) + 1]] <- list(source = pair[1], target = pair[2], value = totals[[key]],
                                       value_text = hl_format_number(totals[[key]], 0))
  }
  values <- vapply(links, `[[`, numeric(1), "value")
  # round() halves to even in R, as Python's round() does
  key <- sort(unique(c(max(values), round(max(values) / 2), min(values))))
  list(nodes = as.list(names), links = links, color = hl_settings()$palette[1],
       key = lapply(key, function(amount) list(value = amount, text = hl_format_number(amount, 0))))
}

arc_stroke <- function(value, largest, style, rules) {
  rules$min_width * style$base + (rules$max_width - rules$min_width) * style$base * value / largest
}

arc_label_shapes <- function(names, xs, baseline_y, measure, style, rules) {
  gap <- rules$label_gap * style$base
  ink <- style$neutral$ink
  widths <- vapply(names, measure, numeric(1), role = "label")
  crowded <- length(names) > 1 && any(widths[-length(widths)] / 2 + widths[-1] / 2 + gap > diff(xs))
  if (!crowded) {
    shapes <- lapply(seq_along(names), function(index) {
      c(shape_text(xs[index], baseline_y - style$descender * style$sizes$label, names[index], "label", ink, "center"),
        part = "node")
    })
    return(list(shapes = shapes, height = line_height(style, "label")))
  }
  tallest <- max(widths)
  shift <- style$cap_height * style$sizes$label / 2
  shapes <- lapply(seq_along(names), function(index) {
    c(shape_text(xs[index] + shift, baseline_y - tallest, names[index], "label", ink, "right"), rotation = 90,
      part = "node")
  })
  list(shapes = shapes, height = tallest)
}

arc_key_shapes <- function(spec, box, largest, measure, style, rules) {
  base <- style$base
  middle <- box[2] + line_height(style, "label") / 2
  baseline <- baseline_for(middle, style, "label")
  x <- box[1]
  shapes <- list()
  for (item in spec$key) {
    sample <- rbind(c(x, middle), c(x + rules$key_line * base, middle))
    shapes[[length(shapes) + 1]] <- list(kind = "line", points = sample,
                                         color = spec$color, width = arc_stroke(item$value, largest, style, rules),
                                         alpha = rules$opacity, part = "key")
    x <- x + rules$key_line * base + style$swatch_text * base
    shapes[[length(shapes) + 1]] <- c(shape_text(x, baseline, item$text, "label", style$neutral$muted), part = "key")
    x <- x + measure(item$text, "label") + rules$key_gap * base
  }
  shapes
}

arc_points <- function(start, end, ground, height, count) {
  angles <- pi * (0:count) / count
  cbind((start + end) / 2 - abs(end - start) / 2 * cos(angles), ground - height * sin(angles))
}

arcs_drawing <- function(spec, box, measure, style) {
  rules <- hl_tokens()$arcs
  base <- style$base
  names <- unlist(spec$nodes)
  values <- vapply(spec$links, function(link) as.numeric(link$value), numeric(1))
  largest <- max(values)
  first <- measure(names[1], "label") / 2
  last <- measure(names[length(names)], "label") / 2
  xs <- box[1] + first + (box[3] - first - last) * (seq_along(names) - 1) / max(length(names) - 1, 1)
  labels <- arc_label_shapes(names, xs, box[2] + box[4], measure, style, rules)
  ground <- box[2] + box[4] - labels$height - rules$label_gap * base
  ceiling <- box[2] + line_height(style, "label") + rules$key_gap * base
  position <- stats::setNames(xs, names)
  spans <- vapply(spec$links, function(link) abs(position[[link$target]] - position[[link$source]]) / 2, numeric(1))
  squeeze <- min(1, (ground - ceiling) / max(spans))
  shapes <- list()
  for (index in order(-values, seq_along(values))) {
    link <- spec$links[[index]]
    start <- position[[link$source]]
    end <- position[[link$target]]
    shapes[[length(shapes) + 1]] <- list(kind = "line", points = arc_points(start, end, ground,
                                                                            abs(end - start) / 2 * squeeze,
                                                                            rules$points),
                                         color = spec$color, width = arc_stroke(values[index], largest, style, rules),
                                         alpha = rules$opacity, role = "arc", source = link$source,
                                         target = link$target)
  }
  radius <- rules$node_radius * base
  angles <- 2 * pi * (0:23) / 24
  for (x in xs) {
    shapes[[length(shapes) + 1]] <- list(kind = "polygon", role = "node_dot", fill = style$neutral$ink,
                                         points = cbind(x + radius * cos(angles), ground + radius * sin(angles)))
  }
  c(shapes, labels$shapes, arc_key_shapes(spec, box, largest, measure, style, rules))
}

#' Arc diagram
#'
#' Nodes on a baseline and an arc above for each pair that exchanges
#' something, its width following the value; without `value` each row counts
#' once. Labels turn upright when they would collide.
#'
#' @param data A data frame, one row per flow (or per pair with a value).
#' @param source,target Columns naming the two ends.
#' @param value Column with the amounts; `NULL` counts rows.
#' @param title,subtitle,caption Frame texts; the title defaults to the columns.
#' @param order Node order along the baseline.
#' @return A ggplot with the hairline frame.
#' @export
hl_arcs <- function(data, source, target, value = NULL, title = NULL, subtitle = NULL, caption = NULL, order = NULL) {
  spec <- arcs_spec(data, source, target, value, order)
  label <- if (is.null(value)) "Count" else humanise(value)
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title %||% paste(label, "from", gsub("_", " ", source), "to", gsub("_", " ", target)),
                  subtitle = subtitle, caption = caption, x = NULL, y = NULL) + theme_hairline(axes = FALSE)
  plot@meta$hairline_drawing <- function(box, measure, style) arcs_drawing(spec, box, measure, style)
  plot@meta$hairline_fit_height <- TRUE
  plot
}
