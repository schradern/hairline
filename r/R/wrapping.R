# Labels that meet the edge of their room, the same rule in every chart as in the Python package's wrapping
# module: a label keeps one line while the chart keeps its minimum size; otherwise it wraps into the room that size
# leaves, and a word wider than that room is an error naming the room it needs. Labels taller than the panel grow
# the figure (plot@meta$hairline_fit_height <- "grow").

# Rounding slack in pt: a label exactly as wide as its room keeps one line.
wrap_tolerance <- 1e-6

wrap_words <- function(content, width, measure, role = "label", weight = NULL) {
  lines <- character()
  current <- ""
  for (word in strsplit(trimws(content), "\\s+")[[1]]) {
    candidate <- if (nzchar(current)) paste(current, word) else word
    if (nzchar(current) && measure(candidate, role, weight) > width) {
      lines <- c(lines, current)
      current <- word
    } else {
      current <- candidate
    }
  }
  c(lines, current)
}

# Width of a wrapped name whose value (`value` pt wide) follows the last line, or stands alone after an empty one.
pair_width <- function(lines, measure, value = 0, space = 0, role = "label", weight = NULL) {
  last <- lines[length(lines)]
  last_width <- if (nzchar(last)) measure(last, role, weight) + space + value else value
  max(c(vapply(lines[-length(lines)], measure, numeric(1), role = role, weight = weight), last_width))
}

# `content` in lines for `room`, a value `value` pt wide after the last: one line when it fits; otherwise wrapped so
# the value fits beside every line, or, when a word is too wide for that, wrapped at the full room with the value on
# a line of its own (an empty last line) if it does not fit after the last.
pair_lines <- function(content, room, measure, value = 0, space = 0, role = "label", weight = NULL) {
  reserve <- if (value > 0) space + value else 0
  if (measure(content, role, weight) + reserve <= room + wrap_tolerance) return(content)
  lines <- wrap_words(content, room - reserve + wrap_tolerance, measure, role, weight)
  if (value == 0 || pair_width(lines, measure, value, space, role, weight) <= room + wrap_tolerance) return(lines)
  lines <- wrap_words(content, room + wrap_tolerance, measure, role, weight)
  if (pair_width(lines, measure, value, space, role, weight) <= room + wrap_tolerance) lines else c(lines, "")
}

# pair_lines(), and an error naming the room needed when a word (or the value) is wider than `room`.
fit_lines <- function(content, room, measure, chart, what, value = 0, space = 0, role = "label", weight = NULL) {
  lines <- pair_lines(content, room, measure, value, space, role, weight)
  need <- pair_width(lines, measure, value, space, role, weight)
  if (need > room + wrap_tolerance) {
    widths <- vapply(lines, measure, numeric(1), role = role, weight = weight)
    widest <- lines[which.max(widths)]
    stop(sprintf(paste("hairline: %s: %s '%s' needs %.0f pt, but the figure leaves %.0f pt for it. Shorten the",
                       "label or use a wider size"), chart, what, if (nzchar(widest)) widest else content, need,
                 max(room, 0)), call. = FALSE)
  }
  lines
}

widest_line <- function(lines, measure, role = "label", weight = NULL) {
  max(c(0, vapply(lines, measure, numeric(1), role = role, weight = weight)))
}

# Centres of blocks `heights` tall, without overlap, as close to `positions` as possible, between `top` and
# `bottom`. Blocks that do not fit stack down from `top` (the figure then grows to hold them).
spread_blocks <- function(positions, heights, top, bottom) {
  count <- length(positions)
  if (count == 0) return(numeric())
  order <- order(positions, seq_len(count))
  sorted <- heights[order]
  offsets <- c(0, cumsum((sorted[-count] + sorted[-1]) / 2))
  shifted <- isotonic(positions[order] - offsets)
  floor_value <- top + sorted[1] / 2
  ceiling_value <- bottom - sorted[count] / 2 - offsets[count]
  shifted <- if (ceiling_value < floor_value) rep(floor_value, count) else
    pmin(pmax(shifted, floor_value), ceiling_value)
  result <- numeric(count)
  result[order] <- shifted + offsets
  result
}
