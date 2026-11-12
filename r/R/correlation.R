# Correlation heatmap, mirroring the Python correlation(): lower triangle, diverging ramp,
# values in the cells, each variable named on the empty diagonal, a binned colour key in the legend row.

correlation_colour <- function(value) {
  colours <- hl_ramp(default_ramp("diverging"))
  colours[round((value + 1) / 2 * (length(colours) - 1)) + 1]
}

# Every column needs two different values in the complete rows; a constant one has no correlation.
correlation_check_varies <- function(rows, columns) {
  if (nrow(rows) < 2) {
    stop(sprintf("hairline: correlation needs at least 2 rows with every column present; got %d", nrow(rows)),
         call. = FALSE)
  }
  for (column in columns) {
    if (length(unique(rows[[column]])) < 2) {
      stop(sprintf(paste("hairline: correlation: '%s' has the same value in every complete row, so its correlations",
                         "are undefined; leave it out"), column), call. = FALSE)
    }
  }
}

correlation_spec <- function(data, columns = NULL, method = "pearson") {
  if (!method %in% c("pearson", "spearman")) {
    stop(sprintf("hairline: correlation: method '%s' must be 'pearson' or 'spearman'", method), call. = FALSE)
  }
  columns <- columns %||% names(data)[vapply(data, is.numeric, logical(1))]
  check_columns(data, columns)
  check_numeric(data, columns, "correlation")
  if (length(columns) < 2) {
    stop(sprintf("hairline: correlation needs at least two numeric columns; got %s",
                 if (length(columns)) paste(columns, collapse = ", ") else "none"), call. = FALSE)
  }
  rows <- data[stats::complete.cases(data[, columns]), columns, drop = FALSE]
  correlation_check_varies(rows, columns)
  matrix <- stats::cor(as.matrix(rows), method = method)
  list(names = as.list(humanise(columns)), matrix = matrix,
       texts = apply(matrix, c(1, 2), hl_format_number, digits = 2),
       colors = apply(matrix, c(1, 2), correlation_colour))
}

# The smallest cell that holds its value: the widest value and the cell's gap on either side. As Python's least_cell().
correlation_least_cell <- function(spec, measure, rules) {
  count <- length(spec$names)
  texts <- unlist(lapply(seq_len(count), function(row) {
    vapply(seq_len(row - 1), function(column) spec$texts[[row, column]], character(1))
  }))
  max(vapply(texts, measure, numeric(1), role = "label")) + 2 * rules$gap_pt
}

# Values print in the cells while cells that hold them leave the names room for their widest word; otherwise the cells
# keep only their colour, which the key reads. As Python's shows_values().
correlation_shows_values <- function(spec, box, measure, rules, style) {
  names <- unlist(spec$names)
  room <- box[3] - length(names) * correlation_least_cell(spec, measure, rules) - rules$label_gap * style$base
  words <- unlist(strsplit(names, "\\s+"))
  room + wrap_tolerance >= max(vapply(words, measure, numeric(1), role = "label"))
}

# Each name on one line while the cells keep their least size; otherwise wrapped into the width that leaves, and a
# word wider than that is refused with the room it needs. As Python's name_lines().
correlation_name_lines <- function(spec, box, measure, style, rules, values) {
  names <- unlist(spec$names)
  least <- if (values) correlation_least_cell(spec, measure, rules) else line_height(style, "label") + 2 * rules$gap_pt
  room <- box[3] - length(names) * least - rules$label_gap * style$base
  lapply(names, fit_lines, room = room, measure = measure, chart = "correlation", what = "the name")
}

# The cell side the width allows beside the names wrapped as `lines`, at most `max_cell` times the base size. As
# Python's width_side().
correlation_width_side <- function(spec, box, measure, style, rules, lines) {
  widest <- max(vapply(lines, widest_line, numeric(1), measure = measure))
  min(rules$max_cell * style$base, (box[3] - widest - rules$label_gap * style$base) / length(lines))
}

# Whether cells as tall as the names' lines still fit the width beside them. As Python's fits_width().
correlation_fits_width <- function(spec, box, measure, style, rules, lines) {
  max(lengths(lines)) * line_height(style, "label") <=
    correlation_width_side(spec, box, measure, style, rules, lines) + wrap_tolerance
}

# Widths to wrap the names into: each run of words of a name that fits `room`, and holds every word. As Python's
# wrap_widths().
correlation_wrap_widths <- function(spec, measure, room) {
  names <- strsplit(unlist(spec$names), "\\s+")
  least <- max(vapply(unlist(names), measure, numeric(1), role = "label"))
  found <- unique(unlist(lapply(names, function(words) {
    unlist(lapply(seq_along(words), function(start) {
      vapply(start:length(words), function(end) measure(paste(words[start:end], collapse = " "), "label"), 0)
    }))
  })))
  sort(found[found >= least - wrap_tolerance & found <= room + wrap_tolerance])
}

# The names wrapped as correlation_name_lines() does, while cells as tall as their lines fit the width; in a column
# too narrow for that, the wrap that leaves the largest cells, and an error saying so when none fits. As Python's
# fitted_lines().
correlation_fitted_lines <- function(spec, box, measure, style, rules, values) {
  lines <- correlation_name_lines(spec, box, measure, style, rules, values)
  if (correlation_fits_width(spec, box, measure, style, rules, lines)) return(lines)
  room <- box[3] - rules$label_gap * style$base
  choices <- lapply(correlation_wrap_widths(spec, measure, room), function(width) {
    lapply(unlist(spec$names), fit_lines, room = width, measure = measure, chart = "correlation", what = "the name")
  })
  fitting <- Filter(function(choice) correlation_fits_width(spec, box, measure, style, rules, choice), choices)
  if (!length(fitting)) {
    stop(sprintf(paste("hairline: correlation: %d names leave no cells beside them that hold their lines in %.0f pt.",
                       "Shorten the names, show fewer variables, or use a wider size"), length(spec$names), box[3]),
         call. = FALSE)
  }
  sides <- vapply(fitting, function(choice) correlation_width_side(spec, box, measure, style, rules, choice), 0)
  fitting[[which.max(sides)]]
}

# Square cells, as large as the box allows beside the names but at most `max_cell` times the base size, and never
# lower than a name's lines. As Python's cell_side().
correlation_side <- function(spec, box, measure, style, rules, lines) {
  count <- length(lines)
  widest <- max(vapply(lines, widest_line, numeric(1), measure = measure))
  side <- min(rules$max_cell * style$base, box[4] / count, (box[3] - widest - rules$label_gap * style$base) / count)
  max(side, max(lengths(lines)) * line_height(style, "label"))
}

correlation_drawing <- function(spec, box, measure, style) {
  rules <- hl_tokens()$correlation
  names <- unlist(spec$names)
  count <- length(names)
  shown <- correlation_shows_values(spec, box, measure, rules, style)
  lines <- correlation_fitted_lines(spec, box, measure, style, rules, shown)
  side <- correlation_side(spec, box, measure, style, rules, lines)
  inset <- rules$gap_pt / 2
  pitch <- line_height(style, "label")
  cells <- values <- labels <- list()
  for (row in seq_len(count)) {
    top <- box[2] + (row - 1) * side
    for (column in seq_len(row - 1)) {
      left <- box[1] + (column - 1) * side
      fill <- spec$colors[[row, column]]
      corners <- rbind(c(left + inset, top + inset), c(left + side - inset, top + inset),
                       c(left + side - inset, top + side - inset), c(left + inset, top + side - inset))
      pair <- paste(names[row], "\u00d7", names[column])
      cells[[length(cells) + 1]] <- tagged_shape(list(kind = "polygon", role = "cell", fill = fill, points = corners),
                                                 pair, paste0(pair, ": ", spec$texts[[row, column]]))
      if (!shown) next
      values[[length(values) + 1]] <- c(shape_text(left + side / 2, baseline_for(top + side / 2, style, "label"),
                                                   spec$texts[[row, column]], "label", contrast_text(fill, style),
                                                   "center"), part = "value")
    }
    first <- top + side / 2 - (length(lines[[row]]) - 1) * pitch / 2
    for (index in seq_along(lines[[row]])) {
      labels[[length(labels) + 1]] <- c(shape_text(box[1] + (row - 1) * side + rules$label_gap * style$base,
                                                   baseline_for(first + (index - 1) * pitch, style, "label"),
                                                   lines[[row]][index], "label", style$neutral$ink), part = "name")
    }
  }
  c(cells, values, labels)
}

contrast_text <- function(fill, style) {
  neutral <- style$neutral
  if (contrast_ratio(fill, neutral$ink) >= contrast_ratio(fill, neutral$surface)) neutral$ink else neutral$surface
}

#' Correlation heatmap
#'
#' Correlations between numeric columns (all of them by default) as the
#' lower triangle on a diverging ramp, values printed in the cells, each
#' variable named on the empty diagonal; rows with gaps are left out.
#'
#' @param data A data frame.
#' @param columns Columns to correlate; `NULL` takes every numeric column.
#' @param method `"pearson"` or `"spearman"`.
#' @param title,subtitle,caption Frame texts; the title defaults to the method.
#' @return A ggplot with the hairline frame.
#' @examples
#' hl_correlation(datasets::mtcars, c("mpg", "disp", "hp", "wt"))
#' @export
hl_correlation <- function(data, columns = NULL, method = "pearson", title = NULL, subtitle = NULL, caption = NULL) {
  spec <- correlation_spec(data, columns, method)
  key <- as.numeric(unlist(hl_tokens()$correlation$key))
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title %||% paste(tools::toTitleCase(method), "correlations"), subtitle = subtitle,
                  caption = caption, x = NULL, y = NULL) + theme_hairline(axes = FALSE) + hl_legend(list()) +
    hl_legend_ramp(vapply(key, correlation_colour, ""), key, format = "number", limits = c(-1, 1))
  plot@meta$hairline_drawing <- function(box, measure, style) correlation_drawing(spec, box, measure, style)
  plot@meta$hairline_fit_height <- TRUE
  plot
}
