# Options every chart shares, applied the same way wherever they appear: axis titles, reference lines, highlighted
# series, a title for the legend row and the order of groups. A chart offers an option by passing it here; each
# function mirrors one in the Python package's charts/options.py.

group_sorts <- c("median", "mean", "n")

#' Options shared by the charts
#'
#' Every chart that has the concept takes these arguments under the same name and applies them the same way.
#'
#' @param min_n Groups (or categories) with fewer values (rows) are left out and named in the caption.
#' @param x_title Axis title under the plot.
#' @param y_title Axis title above the plot, at the outer left edge.
#' @param reference Reference lines on the value axis: a value, several, or a named vector whose names label the
#'   lines, e.g. `c(Target = 0.9)`.
#' @param highlight Groups to keep in colour; the others are drawn in the context grey.
#' @param key_title Title at the start of the legend row, naming what the groups are.
#' @param percent Draw shares (0 to 1) as percent.
#' @param show_n Write each group's n after its name.
#' @param sort Order of the groups: `"median"`, `"mean"` or `"n"`, highest first; `NULL` keeps the given order.
#' @param facet Column whose values each get a panel.
#' @keywords internal
#' @return `NULL`; documentation only.
chart_option_params <- function(min_n, x_title, y_title, reference, highlight, key_title, percent, show_n, sort,
                                facet) {
  NULL
}

# Rows of categories with at least `min_n` rows, and the caption note naming the others. As Python's
# without_small_categories().
without_small_categories <- function(data, category, min_n, chart) {
  if (is.null(min_n)) return(list(data = data, note = NULL))
  check_columns(data, category)
  names <- as.character(data[[category]])
  counts <- table(factor(names, levels = unique(names)))
  dropped <- drop_small(lapply(stats::setNames(as.integer(counts), names(counts)), function(count) rep(1, count)),
                        min_n, chart)
  list(data = data[names %in% names(dropped$groups), , drop = FALSE], note = dropped$note)
}

# A reference value, a vector of them, or a named vector (names as labels), as list(value, label) pairs.
option_references <- function(reference, chart) {
  if (is.null(reference)) return(list())
  if (!is.numeric(reference) || anyNA(reference) || any(!is.finite(reference))) {
    stop(sprintf("hairline: %s: reference must be finite numbers, e.g. 0.9 or c(Target = 0.9); got %s", chart,
                 paste(format(reference), collapse = ", ")), call. = FALSE)
  }
  labels <- names(reference) %||% rep("", length(reference))
  lapply(seq_along(reference), function(index) {
    list(value = unname(reference[index]), label = if (nzchar(labels[index])) labels[index] else NULL)
  })
}

# The series to keep in colour, each one of the chart's groups.
checked_highlight <- function(highlight, names, chart) {
  if (is.null(highlight)) return(NULL)
  unknown <- setdiff(as.character(highlight), names)
  if (length(unknown)) {
    stop(sprintf("hairline: %s: highlight names '%s', which is not a group; groups: %s", chart, unknown[1],
                 paste(names, collapse = ", ")), call. = FALSE)
  }
  as.character(highlight)
}

# Group colours with every group not highlighted in the context grey, for charts that colour by group. As Python's
# highlighted().
highlighted_colours <- function(colours, highlight, names, chart) {
  chosen <- checked_highlight(highlight, names, chart)
  if (!length(chosen)) return(colours)
  colours[!names(colours) %in% chosen] <- context_colour()
  colours
}

# Axis titles, reference lines on the value axis (`reference_axis`), highlighted groups and the legend title, for a
# chart drawn with ggplot2 layers. The axis titles are the frame's: `x_title` under the plot, `y_title` above it.
chart_options <- function(plot, chart, names = character(), x_title = NULL, y_title = NULL, reference = NULL,
                          reference_axis = "y", highlight = NULL, key_title = NULL) {
  if (!is.null(x_title)) plot@meta$hairline_x_title <- x_title
  if (!is.null(y_title)) plot@meta$hairline_y_title <- y_title
  for (line in option_references(reference, chart)) {
    plot <- plot + if (reference_axis == "y") hl_reference(y = line$value, label = line$label) else
      hl_reference(x = line$value, label = line$label)
  }
  chosen <- checked_highlight(highlight, names, chart)
  if (length(chosen)) plot <- plot + hl_highlight(series = chosen)
  if (!is.null(key_title)) plot@meta$hairline_key_title <- key_title
  plot
}

check_sort <- function(sort, allowed, chart) {
  if (!is.null(sort) && !(length(sort) == 1 && sort %in% allowed)) {
    stop(sprintf("hairline: %s: sort '%s' must be one of %s or NULL (the given order)", chart,
                 paste(sort, collapse = ", "), paste0("'", allowed, "'", collapse = ", ")), call. = FALSE)
  }
}

sort_key <- function(values, sort) {
  values <- values[is.finite(values)]
  if (sort == "n") return(length(values))
  if (!length(values)) return(-Inf)
  if (sort == "median") stats::median(values) else mean(values)
}

# Group names, highest median, mean or n first; NULL keeps the given order. Ties keep it too.
sorted_names <- function(names, values_of, sort, chart) {
  check_sort(sort, group_sorts, chart)
  if (is.null(sort)) return(names)
  keys <- vapply(names, function(name) sort_key(as.numeric(values_of(name)), sort), numeric(1))
  names[order(-keys, method = "radix")]
}

# Charts that draw their own shapes (spread, dot plot, Likert): a line above the rows for the reference labels,
# when a reference has one. As Python's reference_line_height().
drawn_reference_height <- function(spec, style) {
  labelled <- any(vapply(spec$references %||% list(), function(line) !is.null(line$label), logical(1)))
  if (labelled) line_height(style, "caption") else 0
}

# Each reference as a dashed line across the rows, its label above them, right of the line. As Python's
# reference_shapes().
drawn_reference_shapes <- function(spec, scale, top, bottom, style) {
  rules <- hl_tokens()$reference
  above <- drawn_reference_height(spec, style)
  baseline <- baseline_for(top + above / 2, style, "caption")
  shapes <- list()
  for (line in spec$references %||% list()) {
    x <- scale(line$value)
    shapes[[length(shapes) + 1]] <- list(kind = "line", points = rbind(c(x, top + above), c(x, bottom)),
                                         color = rules$color, width = style$leader_width, dash = rules$dash,
                                         role = "reference")
    if (!is.null(line$label)) {
      shapes[[length(shapes) + 1]] <- shape_text(x + rules$label_gap * style$sizes$caption, baseline, line$label,
                                                 "caption", style$neutral$faint)
    }
  }
  shapes
}

# Every layer's data tagged with its panel, for facet_wrap(vars(.facet)): a chart builds one panel's layers as it
# would for a single panel, and this places them.
in_facet <- function(layers, panel, panels) {
  lapply(layers, function(layer) {
    if (is.data.frame(layer$data)) layer$data$.facet <- factor(panel, levels = panels)
    layer
  })
}

facet_key <- ".hairline_facet_key"
facet_block <- ".hairline_facet_block"

# For charts that draw facets as blocks of rows on one axis (spread, Likert, dot plot): each row keyed by its facet and
# group ("2025 · Unit A", the name a caption uses), blocks in the order the facet's values first appear, groups in
# `order` within each. The data with the key and block columns, the keys in order and each key's group. As Python's
# facet_rows().
facet_rows <- function(data, group, facet, order, chart) {
  check_columns(data, c(group, facet))
  check_labels(data, facet, chart)
  names <- ordered_names(data[[group]], order, chart, group)
  data <- data[as.character(data[[group]]) %in% names, , drop = FALSE]
  data[[facet_key]] <- paste(as.character(data[[facet]]), "\u00b7", as.character(data[[group]]))
  data[[facet_block]] <- as.character(data[[facet]])
  blocks <- unique(data[[facet_block]])
  keys <- unlist(lapply(blocks, function(block) paste(block, "\u00b7", names)))
  keys <- keys[keys %in% data[[facet_key]]]
  list(data = data, keys = keys, groups = stats::setNames(sub("^.*? \u00b7 ", "", keys, perl = TRUE), keys))
}

# Where row charts (spread, dot plot, forest) write their numbers: beside the plot while it keeps its least width,
# else under each row ("auto"); always beside it ("right"), or always under each row ("below"). As Python's
# check_numbers() and numbers_beside().
number_places <- c("auto", "right", "below")

check_numbers <- function(numbers, chart) {
  if (!is.character(numbers) || length(numbers) != 1 || !numbers %in% number_places) {
    stop(sprintf("hairline: %s: numbers '%s' must be one of 'auto', 'right', 'below'", chart,
                 paste(format(numbers), collapse = ", ")), call. = FALSE)
  }
  numbers
}

# Whether a row chart's numbers sit beside a plot `plot` pt wide: by `place`, and with "right" only while the plot
# keeps `spacing.min_plot_beside`; narrower, the figure stops and says what would fit.
numbers_beside <- function(place, plot, least, base, chart) {
  place <- place %||% "auto"
  if (place == "below") return(FALSE)
  if (place == "auto") return(plot >= least)
  floor <- hl_tokens()$spacing$min_plot_beside * base
  if (plot < floor) {
    stop(layout_error(sprintf(paste("hairline: %s: the numbers beside the plot leave it %.0f pt, and it needs %.0f",
                                    "pt; use a wider size, show fewer numbers, or numbers = \"auto\" (under each",
                                    "row where the plot would be too narrow)"), chart, max(plot, 0), floor)))
  }
  TRUE
}
