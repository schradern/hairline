# Forest plot geometry in pt, the same algorithm as the Python package's forest_geometry: study table, intervals
# with weighted squares, pooled diamond, null and pooled lines, and an x-axis with "favours" labels.

log_breaks <- function(low, high, max_ticks = 7) {
  first <- floor(log10(low)) - 1
  last <- ceiling(log10(high)) + 1
  for (series in list(c(1, 2, 5), 1)) {
    candidates <- sort(round(as.vector(outer(series, 10^(first:last))), 10))
    start <- max(candidates[candidates <= low * (1 + 1e-9)])
    end <- min(candidates[candidates >= high * (1 - 1e-9)])
    ticks <- candidates[candidates >= start & candidates <= end]
    if (length(ticks) <= max_ticks) break
  }
  ticks
}

forest_scale <- function(axis, ratio, left, right) {
  transform <- if (ratio) log else identity
  low <- transform(axis$low)
  high <- transform(axis$high)
  function(value) left + (transform(value) - low) / (high - low) * (right - left)
}

forest_widest <- function(texts, measure, weight = NULL) {
  max(vapply(texts, measure, numeric(1), role = "label", weight = weight))
}

forest_columns <- function(spec, box, measure, rules, base) {
  gap <- rules$column_gap * base
  rows <- spec$rows
  study <- forest_widest(c(spec$study_heading, vapply(rows, `[[`, character(1), "study"), spec$pooled$label),
                         measure)
  extras <- numeric()
  x <- box[1] + study + gap
  for (index in seq_along(spec$columns)) {
    x <- x + forest_widest(c(spec$columns[[index]], vapply(rows, function(row) row$cells[[index]], character(1))),
                           measure)
    extras <- c(extras, x)
    x <- x + gap
  }
  effect <- max(forest_widest(c(spec$effect_heading, vapply(rows, `[[`, character(1), "effect_text")), measure),
                if (is.null(spec$pooled)) 0 else forest_widest(spec$pooled$effect_text, measure, 600))
  has_weight <- !is.null(spec$weight_heading)
  weight <- if (has_weight) forest_widest(c(spec$weight_heading, vapply(rows, `[[`, character(1), "weight_text")),
                                          measure) else 0
  weight_right <- box[1] + box[3]
  effect_right <- weight_right - if (has_weight) weight + gap else 0
  forest_check_span(effect_right - effect - gap - x, rules$min_plot * base, study)
  list(study = box[1], extras = extras, plot = c(x, effect_right - effect - gap), effect = effect_right,
       weight = weight_right)
}

# The table columns must leave room for the intervals; otherwise the axis would run backwards.
forest_check_span <- function(span, least, study) {
  if (span >= least) return(invisible())
  stop(sprintf(paste("hairline: forest: the table columns leave %.0f pt for the intervals, which need at least %.0f",
                     "pt; the study column alone takes %.0f pt. Shorten the longest study labels, drop a column, or",
                     "use a wider size"), max(span, 0), least, study), call. = FALSE)
}

forest_rule <- function(left, right, y, style) {
  list(kind = "line", points = rbind(c(left, y), c(right, y)), color = style$neutral$axis, width = style$leader_width)
}

forest_table_texts <- function(spec, columns, baseline, row, style) {
  ink <- style$neutral$ink
  muted <- style$neutral$muted
  if (is.null(row)) {
    values <- c(spec$study_heading, unlist(spec$columns), spec$effect_heading, spec$weight_heading %||% "")
    colours <- rep(muted, length(values))
    weights <- rep(list(NULL), length(values))
  } else {
    values <- c(row$study, unlist(row$cells), row$effect_text, row$weight_text %||% "")
    colours <- c(ink, rep(muted, length(row$cells)), ink, muted)
    weights <- c(rep(list(NULL), length(values) - 2), list(if (isTRUE(row$bold)) 600 else NULL, NULL))
  }
  rights <- c(columns$extras, columns$effect, columns$weight)
  shapes <- list(shape_text(columns$study, baseline, values[1], "label", colours[1], "left", weights[[1]]))
  for (index in seq_along(rights)) {
    if (nzchar(values[index + 1])) {
      shapes[[length(shapes) + 1]] <- shape_text(rights[index], baseline, values[index + 1], "label",
                                                 colours[index + 1], "right", weights[[index + 1]])
    }
  }
  shapes
}

forest_marker <- function(x, centre, side, shape, colour) {
  half <- side / 2
  if (identical(shape, "dot")) {
    angles <- 2 * pi * (0:23) / 24
    return(list(kind = "polygon", fill = colour, role = "dot",
                points = cbind(x + half * cos(angles), centre + half * sin(angles))))
  }
  list(kind = "polygon", fill = colour, role = "square",
       points = rbind(c(x - half, centre - half), c(x + half, centre - half), c(x + half, centre + half),
                      c(x - half, centre + half)))
}

forest_marks <- function(row, centre, scale, plot, side, spec, style) {
  left <- max(plot[1], scale(row$low))
  right <- min(plot[2], scale(row$high))
  mark <- forest_marker(scale(row$estimate), centre, side, spec$marker %||% "square", spec$color)
  list(list(kind = "line", points = rbind(c(left, centre), c(right, centre)), color = spec$color,
            width = style$data_width, series = row$study),
       c(mark, series = row$study, tip = paste0(row$study, ": ", row$effect_text),
         list(tip_at = c(scale(row$estimate), centre - side / 2))))
}

# Diameter of a dot mark: the same as a scatter point, in every chart.
dot_size <- function(style) 2 * hl_tokens()$lines$point_radius * style$base

forest_sides <- function(spec, rules, base) {
  weights <- lapply(spec$rows, `[[`, "weight")
  if (any(vapply(weights, is.null, logical(1)))) return(rep(rules$plain_square * base, length(weights)))
  weights <- unlist(weights)
  pmax(rules$min_square * base, rules$max_square * base * sqrt(weights / max(weights)))
}
