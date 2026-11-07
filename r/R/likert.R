# Diverging bars for rating scales, mirroring the Python likert(): per item the share of each rating, stacked away
# from the split between disagreement and agreement (a middle level centred on it), the levels collapsed into a few
# named bins that a reader can tell apart, negatively worded items recoded, sections as blocks, and median [IQR] and
# n beside each row.

likert_stats <- c("median", "iqr", "n")

# The scale's levels, given or found in the data; a rating off the scale is refused.
scale_levels <- function(values, levels) {
  found <- sort(unique(as.numeric(values)))
  if (is.null(levels)) return(found)
  scale <- sort(as.numeric(levels))
  off <- setdiff(found, scale)
  if (length(off)) {
    stop(sprintf("hairline: likert: rating %s is not a level of the scale (%s to %s)", spread_level_number(off[1]),
                 spread_level_number(scale[1]), spread_level_number(scale[length(scale)])), call. = FALSE)
  }
  scale
}

# The levels left of the split, at it (a middle level drawn centred) and right of it. By default the split is the
# middle level of an odd scale, else midway between the two middle levels.
scale_sides <- function(levels, split) {
  if (is.null(split)) {
    middle <- length(levels) %/% 2
    split <- if (length(levels) %% 2) levels[middle + 1] else (levels[middle] + levels[middle + 1]) / 2
  }
  sides <- list(left = levels[levels < split], middle = levels[levels == split], right = levels[levels > split])
  if (!length(sides$left) || !length(sides$right)) {
    stop(sprintf("hairline: likert: split %s must leave levels on both sides", spread_level_number(split)),
         call. = FALSE)
  }
  sides
}

bin_label <- function(levels) {
  first <- spread_level_number(levels[1])
  if (length(levels) == 1) first else paste0(first, "\u2013", spread_level_number(levels[length(levels)]))
}

# A side's bins: each level its own up to `likert.levels_per_side`, else two, the outer one holding the extreme half
# (1-2 beside 3-5).
side_bins <- function(levels, outer_first) {
  if (length(levels) <= hl_tokens()$likert$levels_per_side) return(as.list(levels))
  half <- length(levels) %/% 2
  cut <- if (outer_first) half else length(levels) - half
  list(levels[seq_len(cut)], levels[-seq_len(cut)])
}

# Bins as named: each a range of levels on one side (or the middle level), every level in exactly one.
given_bins <- function(bins, sides) {
  every <- c(sides$left, sides$middle, sides$right)
  found <- lapply(names(bins), function(name) {
    held <- every[every >= bins[[name]][1] & every <= bins[[name]][2]]
    one_side <- any(vapply(sides, function(side) length(side) > 0 && all(held %in% side), logical(1)))
    if (!length(held) || !one_side) {
      stop(sprintf("hairline: likert: bin '%s' must hold levels of one side of the split", name), call. = FALSE)
    }
    list(name = name, levels = held)
  })
  used <- unlist(lapply(found, `[[`, "levels"))
  missing <- every[vapply(every, function(level) sum(used == level) != 1, logical(1))]
  if (length(missing)) {
    stop(sprintf("hairline: likert: bins must hold every level once; %s is not", spread_level_number(missing[1])),
         call. = FALSE)
  }
  found[order(vapply(found, function(entry) entry$levels[1], numeric(1)))]
}

# Bins left to right with their side and colour from the diverging ramp, the middle colour for a middle level. The
# high half takes the ramp's first pole (blue on the default ramp): agreement reads cool, disagreement warm.
scale_bins <- function(levels, split, bins, ramp_name = NULL) {
  sides <- scale_sides(levels, split)
  named <- if (length(bins)) {
    given_bins(bins, sides)
  } else {
    groups <- c(side_bins(sides$left, TRUE), if (length(sides$middle)) list(sides$middle),
                side_bins(sides$right, FALSE))
    lapply(groups, function(group) list(name = bin_label(group), levels = group))
  }
  starts <- vapply(named, function(entry) entry$levels[1], numeric(1))
  lefts <- named[starts %in% sides$left]
  middles <- named[starts %in% sides$middle]
  rights <- named[starts %in% sides$right]
  reach <- max(length(lefts), length(rights))
  colours <- rev(interpolate_colors(hl_ramp(ramp_name %||% default_ramp("diverging")), 2 * reach + 1))
  c(lapply(seq_along(lefts), function(index) {
    c(lefts[[index]], side = "left", color = colours[reach - length(lefts) + index])
  }), lapply(middles, function(entry) c(entry, side = "middle", color = colours[reach + 1])),
  lapply(seq_along(rights), function(index) c(rights[[index]], side = "right", color = colours[reach + 1 + index])))
}

# Median, IQR and n on the data's levels, in spread's key-number style.
likert_pairs <- function(values, stats) {
  limits <- level_quantiles(values, c(0.25, 0.5, 0.75))
  parts <- list(median = c(word("median"), spread_level_number(limits[2])),
                iqr = c(word("iqr"), paste0(spread_level_number(limits[1]), "\u2013", spread_level_number(limits[3]))),
                n = c("n", hl_format_number(length(values), 0)))
  unname(parts[stats])
}

# Per item its label, section, n, the share in each bin (in percent) and its key numbers.
likert_rows <- function(data, item, rating, names, scale) {
  low <- scale$levels[1]
  high <- scale$levels[length(scale$levels)]
  rows <- lapply(names, function(name) {
    values <- as.numeric(data[[rating]][as.character(data[[item]]) == name])
    values <- values[!is.na(values)]
    if (name %in% scale$reverse) values <- low + high - values
    if (!length(values)) return(NULL)
    label <- if (name %in% scale$reverse) paste0(name, " (", word("reversed"), ")") else name
    list(name = label, item = name, section = if (length(scale$sections)) unname(scale$sections[[name]]),
         n = length(values), shares = vapply(scale$bins, function(entry) mean(values %in% entry$levels) * 100, 0),
         pairs = likert_pairs(values, scale$stats))
  })
  Filter(Negate(is.null), rows)
}

likert_balance <- function(row, bins) {
  sum(row$shares * vapply(bins, function(entry) switch(entry$side, left = -1, middle = 0, right = 1), 0))
}

# Rows by section (in the order sections first appear), then by agreement less disagreement when sorted.
likert_order <- function(rows, bins, sort) {
  sections <- vapply(rows, function(row) row$section %||% "", character(1))
  rank <- match(sections, unique(sections))
  if (identical(sort, "balance")) {
    return(rows[order(rank, -vapply(rows, likert_balance, 0, bins = bins))])
  }
  rows[order(rank)]
}

# One axis in percent either side of the split, as far as the longer side reaches, labelled outward from 0.
likert_axis <- function(rows, bins) {
  side <- function(row, name) {
    weights <- vapply(bins, function(entry) {
      if (entry$side == "middle") 0.5 else if (entry$side == name) 1 else 0
    }, 0)
    sum(row$shares * weights)
  }
  reach <- max(vapply(rows, function(row) max(side(row, "left"), side(row, "right")), 0))
  half <- spread_axis(0, reach, FALSE, TRUE)
  list(breaks = c(-rev(half$breaks[-1]), half$breaks), labels = c(rev(half$labels[-1]), half$labels),
       low = -half$high, high = half$high)
}

likert_check_options <- function(stats, sort, reverse, names) {
  unknown <- setdiff(stats, likert_stats)
  if (length(unknown)) {
    stop(sprintf("hairline: likert: unknown statistic '%s'; use any of %s", unknown[1],
                 paste(likert_stats, collapse = ", ")), call. = FALSE)
  }
  if (!is.null(sort) && !identical(sort, "balance")) {
    stop(sprintf("hairline: likert: sort '%s' must be 'balance' or NULL", sort), call. = FALSE)
  }
  missing <- setdiff(as.character(reverse), names)
  if (length(missing)) {
    stop(sprintf("hairline: likert: reverse names '%s', which is not an item", missing[1]), call. = FALSE)
  }
}

likert_spec <- function(data, item, rating, levels = NULL, split = NULL, bins = NULL, group = NULL,
                        reverse = character(), order = NULL, sort = NULL, stats = likert_stats, axis_title = NULL,
                        ramp_name = NULL) {
  check_columns(data, c(item, rating, group))
  check_labels(data, item, "likert")
  check_numeric(data, rating, "likert")
  names <- ordered_names(data[[item]], order, "likert", item)
  likert_check_options(stats, sort, reverse, names)
  values <- as.numeric(data[[rating]])
  scale <- list(levels = scale_levels(values[!is.na(values)], levels), stats = stats,
                reverse = as.character(reverse),
                sections = if (!is.null(group)) coarse_groups(data, item, group, "likert"))
  scale$bins <- scale_bins(scale$levels, split, bins, ramp_name)
  rows <- likert_rows(data, item, rating, names, scale)
  if (!length(rows)) {
    stop(sprintf("hairline: likert: no ratings to draw; '%s' is empty or missing in every row", rating),
         call. = FALSE)
  }
  rows <- likert_order(rows, scale$bins, sort)
  list(rows = rows, bins = scale$bins, axis = likert_axis(rows, scale$bins),
       axis_title = axis_title %||% word("respondents_share"))
}

#' Diverging bars for rating scales
#'
#' Ratings per item (one row per answer), as diverging bars: the share of each
#' bin stacked away from the split between the low and the high half of the
#' scale, a middle level centred on it. By default each side keeps its levels
#' up to `likert.levels_per_side`, else two bins, so a ten-point scale reads
#' 1-2, 3-5 | 6-8, 9-10 and its colours can be told apart. Negatively worded
#' items (`reverse`) are recoded and marked, so colour keeps one meaning. The
#' median, IQR (on the data's levels) and n stand beside each row; the binned
#' key sits in the legend row.
#'
#' @param data A data frame, one row per answer.
#' @param item,rating Columns: the statement and its rating.
#' @param levels The scale's levels; by default the ratings found.
#' @param split Where the scale divides; by default its middle (the middle level of an odd scale is centred).
#' @param bins Named ranges of levels, e.g. `list("1-2" = c(1, 2), "3-5" = c(3, 5))`.
#' @param group Column whose values draw the items in blocks under their section's name.
#' @param reverse Items worded negatively, recoded (low becomes high) and marked.
#' @param order Item order.
#' @param sort `"balance"` orders a block by agreement less disagreement; `NULL` keeps the order.
#' @param stats Key numbers beside each row: any of `"median"`, `"iqr"`, `"n"`.
#' @param axis_title Title under the axis (default: the locale's "% of respondents").
#' @param key_title Title of the binned key.
#' @param ramp A diverging ramp's name; the high half takes its first pole.
#' @param title,subtitle,caption Frame texts.
#' @param size Size preset, as in [hl_save()].
#' @return A ggplot with the hairline frame.
#' @examples
#' set.seed(1)
#' answers <- data.frame(statement = rep(c("Easy to book a visit", "Explanations were clear"), each = 40),
#'                       rating = c(sample(4:10, 40, TRUE), sample(1:8, 40, TRUE)))
#' hl_likert(answers, "statement", "rating", levels = 1:10)
#' @export
hl_likert <- function(data, item, rating, levels = NULL, split = NULL, bins = NULL, group = NULL,
                      reverse = character(), order = NULL, sort = NULL, stats = likert_stats, axis_title = NULL,
                      key_title = NULL, ramp = NULL, title = NULL, subtitle = NULL, caption = NULL, size = "double") {
  check_size_preset(size)
  spec <- likert_spec(data, item, rating, levels, split, bins, group, reverse, order, sort, stats, axis_title, ramp)
  count <- length(spec$bins)
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title %||% paste(humanise(rating), "by", gsub("_", " ", item)), subtitle = subtitle,
                  caption = caption, x = NULL, y = NULL) + theme_hairline(axes = FALSE) + hl_legend(list()) +
    hl_legend_ramp(vapply(spec$bins, `[[`, "", "color"), seq_len(count) / count, key_title,
                   labels = vapply(spec$bins, `[[`, "", "name"))
  plot@meta$hairline_drawing <- function(box, measure, style) likert_drawing(spec, box, measure, style)
  plot@meta$hairline_fit_height <- TRUE
  plot@meta$hairline_size <- size
  plot
}

# Each bin's span in percent: a middle level centred on the split, the bins of each side stacked outward from it,
# the one nearest the split first.
likert_segments <- function(row, bins) {
  shares <- stats::setNames(row$shares, vapply(bins, `[[`, "", "name"))
  sides <- vapply(bins, `[[`, "", "side")
  middle <- sum(shares[sides == "middle"])
  spans <- lapply(bins[sides == "middle"], function(entry) list(entry = entry, low = -middle / 2, high = middle / 2))
  edge <- -middle / 2
  for (entry in rev(bins[sides == "left"])) {
    spans[[length(spans) + 1]] <- list(entry = entry, low = edge - shares[[entry$name]], high = edge)
    edge <- edge - shares[[entry$name]]
  }
  edge <- middle / 2
  for (entry in bins[sides == "right"]) {
    spans[[length(spans) + 1]] <- list(entry = entry, low = edge, high = edge + shares[[entry$name]])
    edge <- edge + shares[[entry$name]]
  }
  lapply(spans, function(span) c(span, share = shares[[span$entry$name]]))
}

# One rectangle per bin that holds answers, a surface gap between neighbours, each a tooltip target.
likert_bars <- function(row, bins, centre, line, scale, style) {
  rules <- hl_tokens()$likert
  half <- rules$bar * line / 2
  shapes <- list()
  for (span in likert_segments(row, bins)) {
    if (span$share <= 0) next
    left <- scale(span$low)
    right <- scale(span$high)
    points <- rbind(c(left, centre - half), c(right, centre - half), c(right, centre + half), c(left, centre + half))
    shapes[[length(shapes) + 1]] <- list(kind = "polygon", points = points, fill = span$entry$color,
                                         edge = style$neutral$surface, edge_width = rules$gap_pt, role = "bar",
                                         series = span$entry$name,
                                         tip = paste0(row$name, ": ", span$entry$name, ", ",
                                                      hl_format_percent(span$share / 100, 0)),
                                         tip_at = c((left + right) / 2, centre - half))
  }
  shapes
}

# Rows keep spread's pitch (the figure's height follows them); a heading takes one line.
likert_drawing <- function(spec, box, measure, style) {
  rules <- hl_tokens()$spread
  layout <- spread_layout(spec, box, measure, style, rules)
  left <- layout$plot[1]
  right <- layout$plot[2]
  lead <- line_height(style, "label")
  scale <- forest_scale(spec$axis, FALSE, left, right)
  line <- rules$row_pitch * lead
  pitch <- line + if (layout$under) lead else 0
  lines <- section_lines(spec$rows)
  heights <- vapply(lines, function(entry) if (entry$kind == "heading") line else pitch, numeric(1))
  bottom <- box[2] + sum(heights)
  shapes <- lapply(spec$axis$breaks, function(value) {
    list(kind = "line", points = rbind(c(scale(value), box[2]), c(scale(value), bottom)), color = style$neutral$grid,
         width = style$grid, role = "grid")
  })
  top <- box[2]
  headings <- 0
  for (index in seq_along(lines)) {
    entry <- lines[[index]]$entry
    centre <- top + line / 2
    baseline <- baseline_for(centre, style, "label")
    top <- top + heights[index]
    if (lines[[index]]$kind == "heading") {
      shapes <- c(shapes, heading_shapes(entry, headings, FALSE, box[1], baseline, measure, style))
      headings <- headings + 1
      next
    }
    shapes <- c(shapes, likert_bars(entry, spec$bins, centre, line, scale, style),
                list(shape_text(box[1], baseline, entry$name, "label", style$neutral$ink)),
                spread_pair_texts(entry$pairs, layout$lefts, baseline + if (layout$under) lead else 0, measure, style))
  }
  split <- list(kind = "line", points = rbind(c(scale(0), box[2]), c(scale(0), bottom)), color = style$neutral$ink,
                width = hl_tokens()$likert$centre_width * style$base, role = "split")
  axis <- list(axis = spec$axis, favours = NULL, null = NULL)
  c(shapes, list(split), forest_axis_shapes(axis, scale, c(left, right), bottom, style, rules),
    spread_title_shape(spec, right, bottom, style, rules))
}
