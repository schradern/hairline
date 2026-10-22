# Forest plot geometry in pt, the same algorithm as the Python package's forest_geometry: study table, intervals
# with weighted squares, pooled diamond, null and pooled lines, and an x-axis with "favours" labels.

# Ratio breaks are rounded to this many decimals, so a ratio axis reaches from 10^-ratio_places to 10^ratio_places.
ratio_places <- 10

log_breaks <- function(low, high, max_ticks = 7) {
  first <- floor(log10(low)) - 1
  last <- ceiling(log10(high)) + 1
  for (series in list(c(1, 2, 5), 1)) {
    candidates <- sort(round(as.vector(outer(series, 10^(first:last))), ratio_places))
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

# Widths of the study column, the extra columns, the effect column and the weight column (0 without).
forest_column_widths <- function(spec, measure) {
  rows <- spec$rows
  study <- forest_widest(c(spec$study_heading, vapply(rows, `[[`, character(1), "study"), spec$pooled$label),
                         measure)
  extras <- vapply(seq_along(spec$columns), function(index) {
    forest_widest(c(spec$columns[[index]], vapply(rows, function(row) row$cells[[index]], character(1))), measure)
  }, numeric(1))
  effect <- max(forest_widest(c(spec$effect_heading, vapply(rows, `[[`, character(1), "effect_text")), measure),
                if (is.null(spec$pooled)) 0 else forest_widest(spec$pooled$effect_text, measure, 600))
  weight <- if (is.null(spec$weight_heading)) 0 else
    forest_widest(c(spec$weight_heading, vapply(rows, `[[`, character(1), "weight_text")), measure)
  list(study = study, extras = extras, effect = effect, weight = weight)
}

forest_right_edges <- function(widths, start, gap) start + cumsum(widths) + gap * (seq_along(widths) - 1)

# Left edge of the study column, right edges of the extra, effect and weight columns and the plot span. The columns
# sit beside the plot while it keeps `min_plot`; on a narrower figure they move to a line under each row (`under`),
# from the study column's left edge, and the plot spans the width the study labels leave.
forest_columns <- function(spec, box, measure, rules, base) {
  gap <- rules$column_gap * base
  least <- rules$min_plot * base
  right <- box[1] + box[3]
  widths <- forest_column_widths(spec, measure)
  weighted <- !is.null(spec$weight_heading)
  beside <- forest_right_edges(widths$extras, box[1] + widths$study + gap, gap)
  plot_left <- if (length(beside)) beside[length(beside)] + gap else box[1] + widths$study + gap
  effect_right <- right - if (weighted) widths$weight + gap else 0
  if (effect_right - widths$effect - gap - plot_left >= least) {
    return(list(study = box[1], extras = beside, plot = c(plot_left, effect_right - widths$effect - gap),
                effect = effect_right, weight = right, right = right, under = FALSE))
  }
  line <- c(widths$extras, widths$effect, if (weighted) widths$weight)
  forest_check_room(box[3], sum(line) + gap * (length(line) - 1), least, widths$study, gap)
  under <- forest_right_edges(line, box[1], gap)
  count <- length(widths$extras)
  list(study = box[1], extras = under[seq_len(count)], plot = c(box[1] + widths$study + gap, right),
       effect = under[count + 1], weight = if (weighted) under[length(under)] else right, right = right,
       under = TRUE)
}

# Under the rows, a line of columns and a row of study label and intervals must each fit the width.
forest_check_room <- function(width, block, least, study, gap) {
  need <- max(block, study + gap + least)
  if (width >= need) return(invisible())
  stop(sprintf(paste("hairline: forest: the figure leaves %.0f pt for the table, which needs at least %.0f pt: the",
                     "columns take %.0f pt in one line under each study, the study labels %.0f pt beside intervals",
                     "of %.0f pt. Shorten the longest study labels, drop a column, or use a wider size"), width, need,
               block, study, least), call. = FALSE)
}

forest_rule <- function(left, right, y, style) {
  list(kind = "line", points = rbind(c(left, y), c(right, y)), color = style$neutral$axis, width = style$leader_width)
}

# One table row: the headings when `row` is NULL, else study, cells, effect and weight of that row; the columns after
# the study label one line lower (`lead`) when they sit under the row.
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
  lead <- columns$lead %||% 0
  shapes <- list(shape_text(columns$study, baseline, values[1], "label", colours[1], "left", weights[[1]]))
  for (index in seq_along(rights)) {
    if (nzchar(values[index + 1])) {
      shapes[[length(shapes) + 1]] <- shape_text(rights[index], baseline + lead, values[index + 1], "label",
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
