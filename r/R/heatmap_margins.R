# Marginal bars of a heatmap: each column's mean (or sum) of `z` as a bar above it, each row's as a bar to its right,
# in grey so the ramp keeps the colour, the largest of each written at its end. The bars add room to the figure
# rather than take it from the cells. Mirrors the Python package's charts/heatmap_margins.py.

heatmap_margin_kinds <- c(mean = "mean", sum = "sum")

heatmap_check_margins <- function(margins, chart) {
  known <- is.character(margins) && length(margins) == 1 && margins %in% names(heatmap_margin_kinds)
  if (!is.null(margins) && !known) {
    stop(sprintf("hairline: %s: margins '%s' must be 'mean', 'sum' or NULL", chart, paste(margins, collapse = ", ")),
         call. = FALSE)
  }
}

# The mean or sum of the known values; NA when none is known. As Python's aggregated().
heatmap_aggregated <- function(values, kind) {
  known <- values[is.finite(values)]
  if (!length(known)) return(NA_real_)
  if (kind == "mean") mean(known) else sum(known)
}

# Each column's and each row's mean or sum, written as the cells' values are. As Python's margin_spec().
heatmap_margin_spec <- function(grid, kind, percent, chart) {
  columns <- apply(grid, 2, heatmap_aggregated, kind = kind)
  rows <- apply(grid, 1, heatmap_aggregated, kind = kind)
  known <- c(columns, rows)
  known <- known[!is.na(known)]
  if (min(known) < 0) {
    stop(sprintf(paste("hairline: %s: margins draw bars from zero, so they need a %s of zero or more in every row and",
                       "column; the lowest is %s"), chart, kind, format(min(known))), call. = FALSE)
  }
  texts <- grid_value_texts(known, percent)
  counted <- sum(!is.na(columns))
  list(columns = unname(columns), rows = unname(rows),
       texts = list(columns = heatmap_margin_placed(columns, texts[seq_len(counted)]),
                    rows = heatmap_margin_placed(rows, texts[-seq_len(counted)])),
       word = word(heatmap_margin_kinds[[kind]]))
}

# Texts in the places of the known values, "" where a value is missing.
heatmap_margin_placed <- function(values, texts) {
  placed <- rep("", length(values))
  placed[!is.na(values)] <- texts
  placed
}

# The first of the largest values. As Python's peak().
heatmap_margin_peak <- function(values) which.max(ifelse(is.na(values), 0, values))

# The bars' values with their colour, the band, gaps and the widest peak label in pt. As Python's margin_scene().
heatmap_margin_scene <- function(margins, measure, style) {
  if (is.null(margins)) return(NULL)
  rules <- hl_tokens()$heatmap
  base <- style$base
  label <- measure(margins$texts$rows[[heatmap_margin_peak(margins$rows)]], "label")
  c(margins, list(color = style$neutral$axis, band = rules$margin_band * base, gap = rules$margin_gap * base,
                  pad = rules$margin_pad * base, bar_gap = rules$margin_bar_gap, label_width = label))
}

# The room the bars take above the cells and to their right. As Python's margin_reserve().
heatmap_margin_reserve <- function(scene, line) {
  if (is.null(scene)) return(c(0, 0))
  c(line + scene$pad + scene$band + scene$gap, scene$gap + scene$band + scene$pad + scene$label_width)
}

heatmap_margin_bar <- function(left, top, right, bottom, colour) {
  list(kind = "polygon", points = rbind(c(left, top), c(right, top), c(right, bottom), c(left, bottom)),
       fill = colour, part = "margin")
}

# A bar above each column with a value, rising from the band's foot, the largest written above it. As Python's
# column_bars().
heatmap_column_bars <- function(scene, margins, plot, glyphs) {
  xs <- scene$x_edges
  largest <- heatmap_margin_peak(margins$columns)
  foot <- plot[2] - margins$gap
  top <- max(margins$columns[largest], 0)
  shapes <- list()
  for (column in seq_along(margins$columns)) {
    value <- margins$columns[column]
    if (is.na(value)) next
    inset <- (xs[column + 1] - xs[column]) * plot[3] * margins$bar_gap / 2
    left <- plot[1] + xs[column] * plot[3] + inset
    right <- plot[1] + xs[column + 1] * plot[3] - inset
    height <- if (top > 0) margins$band * value / top else 0
    where <- paste(Filter(nzchar, c(scene$titles$x, scene$tips$x[[column]])), collapse = " ")
    shapes[[length(shapes) + 1]] <- tagged_shape(heatmap_margin_bar(left, foot - height, right, foot, margins$color),
                                                 where, paste0(where, ": ", margins$word, " ",
                                                               margins$texts$columns[column]))
    if (column == largest) {
      shapes[[length(shapes) + 1]] <- c(shape_text((left + right) / 2, foot - height - margins$pad - glyphs$descender,
                                                   margins$texts$columns[column], "label", glyphs$ticks, "center"),
                                        part = "margin")
    }
  }
  shapes
}

# A bar to the right of each row with a value, from the band's start, the largest written after it; it belongs to
# its row's series. As Python's row_bars().
heatmap_row_bars <- function(scene, margins, plot, glyphs) {
  ys <- scene$y_edges
  largest <- heatmap_margin_peak(margins$rows)
  start <- plot[1] + plot[3] + margins$gap
  top <- max(margins$rows[largest], 0)
  shapes <- list()
  for (row in seq_along(margins$rows)) {
    value <- margins$rows[row]
    if (is.na(value)) next
    inset <- (ys[row + 1] - ys[row]) * plot[4] * margins$bar_gap / 2
    upper <- plot[2] + (1 - ys[row + 1]) * plot[4] + inset
    lower <- plot[2] + (1 - ys[row]) * plot[4] - inset
    reach <- if (top > 0) margins$band * value / top else 0
    where <- paste(Filter(nzchar, c(scene$titles$y, scene$tips$y[[row]])), collapse = " ")
    shapes[[length(shapes) + 1]] <- tagged_shape(heatmap_margin_bar(start, upper, start + reach, lower,
                                                                    margins$color),
                                                 where, paste0(where, ": ", margins$word, " ",
                                                               margins$texts$rows[row]))
    if (row == largest) {
      shapes[[length(shapes) + 1]] <- c(shape_text(start + reach + margins$pad, (upper + lower) / 2 + glyphs$cap / 2,
                                                   margins$texts$rows[row], "label", glyphs$ticks), part = "margin")
    }
  }
  shapes
}

# The bars above the columns and right of the rows, with their peak labels; none without margins. As Python's
# margin_shapes().
heatmap_margin_shapes <- function(scene, plot) {
  margins <- scene$margins
  if (is.null(margins)) return(list())
  c(heatmap_column_bars(scene, margins, plot, scene$text), heatmap_row_bars(scene, margins, plot, scene$text))
}
