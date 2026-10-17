# Correlation heatmap, mirroring the Python correlation(): lower triangle, diverging ramp,
# values in the cells, each variable named on the empty diagonal, colour key in the legend row.

correlation_colour <- function(value) {
  colours <- hl_ramp(hl_tokens()$correlation$ramp)
  colours[round((value + 1) / 2 * (length(colours) - 1)) + 1]
}

correlation_spec <- function(data, columns = NULL, method = "pearson") {
  if (!method %in% c("pearson", "spearman")) {
    stop(sprintf("hairline: correlation: method '%s' must be 'pearson' or 'spearman'", method), call. = FALSE)
  }
  columns <- columns %||% names(data)[vapply(data, is.numeric, logical(1))]
  check_columns(data, columns)
  if (length(columns) < 2) {
    stop(sprintf("hairline: correlation needs at least two numeric columns; got %s",
                 if (length(columns)) paste(columns, collapse = ", ") else "none"), call. = FALSE)
  }
  rows <- data[stats::complete.cases(data[, columns]), columns, drop = FALSE]
  matrix <- stats::cor(as.matrix(rows), method = method)
  list(names = as.list(humanise(columns)), matrix = matrix,
       texts = apply(matrix, c(1, 2), hl_format_number, digits = 2),
       colors = apply(matrix, c(1, 2), correlation_colour))
}

correlation_drawing <- function(spec, box, measure, style) {
  rules <- hl_tokens()$correlation
  names <- unlist(spec$names)
  count <- length(names)
  widest <- max(vapply(names, measure, numeric(1), role = "label"))
  side <- min(rules$max_cell * style$base, box[4] / count, (box[3] - widest) / count)
  inset <- rules$gap_pt / 2
  cells <- values <- labels <- list()
  for (row in seq_len(count)) {
    top <- box[2] + (row - 1) * side
    for (column in seq_len(row - 1)) {
      left <- box[1] + (column - 1) * side
      fill <- spec$colors[[row, column]]
      corners <- rbind(c(left + inset, top + inset), c(left + side - inset, top + inset),
                       c(left + side - inset, top + side - inset), c(left + inset, top + side - inset))
      cells[[length(cells) + 1]] <- list(kind = "polygon", role = "cell", fill = fill, points = corners)
      values[[length(values) + 1]] <- c(shape_text(left + side / 2, baseline_for(top + side / 2, style, "label"),
                                                   spec$texts[[row, column]], "label", contrast_text(fill, style),
                                                   "center"), part = "value")
    }
    labels[[length(labels) + 1]] <- c(shape_text(box[1] + (row - 1) * side + rules$label_gap * style$base,
                                                 baseline_for(top + side / 2, style, "label"), names[row], "label",
                                                 style$neutral$ink), part = "name")
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
#' @export
hl_correlation <- function(data, columns = NULL, method = "pearson", title = NULL, subtitle = NULL, caption = NULL) {
  spec <- correlation_spec(data, columns, method)
  key <- lapply(hl_tokens()$correlation$key, function(value) {
    list(kind = "square", colour = correlation_colour(value),
         label = hl_format_number(value, if (value == round(value)) 0 else 1))
  })
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title %||% paste(tools::toTitleCase(method), "correlations"), subtitle = subtitle,
                  caption = caption, x = NULL, y = NULL) + theme_hairline(axes = FALSE) + hl_legend(key)
  plot@meta$hairline_drawing <- function(box, measure, style) correlation_drawing(spec, box, measure, style)
  plot@meta$hairline_fit_height <- TRUE
  plot
}
