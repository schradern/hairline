# Extract what the frame needs from a built ggplot: panels with their axes, labels, legend items, headers.

neighbour_grob <- function(table, prefix, panel_t, panel_l, side) {
  layout <- table$layout
  t <- if (side == "left") panel_t else panel_t + 1
  l <- if (side == "left") panel_l - 1 else panel_l
  cell <- which(startsWith(layout$name, prefix) & layout$t == t & layout$l == l)
  if (length(cell) == 0) ggplot2::zeroGrob() else table$grobs[[cell[1]]]
}

edge_hjust <- function(offsets) {
  tolerance <- hl_tokens()$ticks$edge_tolerance
  ifelse(offsets <= tolerance, 0, ifelse(offsets >= 1 - tolerance, 1, 0.5))
}

# Labels at the plot's left or right edge align inward, as in the Python package.
align_edge_labels <- function(grob) {
  if (inherits(grob, "text") && length(grob$label) > 0) {
    grob$hjust <- edge_hjust(as.numeric(grob$x))
    return(grob)
  }
  if (inherits(grob, "gtable")) {
    grob$grobs <- lapply(grob$grobs, align_edge_labels)
  } else if (length(grob$children)) {
    grob <- grid::setChildren(grob, do.call(grid::gList, lapply(grob$children, align_edge_labels)))
  }
  grob
}

facet_labels <- function(built) {
  facet <- built@layout$layout
  facet <- facet[order(facet$ROW, facet$COL), , drop = FALSE]
  vars <- setdiff(names(facet), c("PANEL", "ROW", "COL", "SCALE_X", "SCALE_Y", "COORD"))
  facet_label <- function(row) {
    paste(vapply(vars, function(var) as.character(facet[[var]][row]), character(1)), collapse = ", ")
  }
  labels <- if (length(vars) == 0) rep(list(NULL), nrow(facet)) else lapply(seq_len(nrow(facet)), facet_label)
  list(rows = facet$ROW, cols = facet$COL, labels = labels)
}

extract_panels <- function(table, built) {
  layout <- table$layout
  cells <- which(startsWith(layout$name, "panel"))
  rows_t <- sort(unique(layout$t[cells]))
  cols_l <- sort(unique(layout$l[cells]))
  facets <- facet_labels(built)
  lapply(seq_along(facets$rows), function(index) {
    t <- rows_t[facets$rows[index]]
    l <- cols_l[facets$cols[index]]
    cell <- cells[layout$t[cells] == t & layout$l[cells] == l][1]
    list(grob = table$grobs[[cell]], row = facets$rows[index], col = facets$cols[index],
         label = facets$labels[[index]], axis_l = neighbour_grob(table, "axis-l", t, l, "left"),
         axis_b = align_edge_labels(neighbour_grob(table, "axis-b", t, l, "below")))
  })
}

plot_label <- function(built, key) {
  value <- built@plot@labels[[key]]
  if (is.null(value) || inherits(value, "waiver") || identical(value, "")) NULL else as.character(value)
}

panel_aspect <- function(built) {
  ratio <- built@layout$coord$ratio
  if (is.null(ratio)) return(NULL)
  params <- built@layout$panel_params[[1]]
  ratio * diff(params$y$continuous_range) / diff(params$x$continuous_range)
}

fitted_box <- function(box, aspect) {
  if (is.null(aspect)) return(box)
  width <- min(box[3], box[4] / aspect)
  c(box[1] + (box[3] - width) / 2, box[2], width, width * aspect)
}

# Per-panel extras a chart stores in its meta, by panel order: row blocks (lanes, swimlanes) and a numbers column
# right of the panel (an n per bar: a list of list(position, label, value) in the panel's y data).
with_panel_extras <- function(panels, meta) {
  blocks <- meta$hairline_blocks %||% list()
  numbers <- meta$hairline_side_numbers %||% list()
  for (index in seq_along(panels)) {
    if (index <= length(blocks)) panels[[index]]["blocks"] <- list(blocks[[index]])
    if (index <= length(numbers)) panels[[index]]["side_numbers"] <- list(numbers[[index]])
  }
  panels
}

frame_parts <- function(table, built) {
  settings <- built@plot@meta$hairline_settings %||% hl_settings()
  meta <- built@plot@meta
  panels <- with_panel_extras(extract_panels(table, built), meta)
  flipped <- inherits(built@layout$coord, "CoordFlip")
  list(settings = settings, panels = panels, ramp_key = meta$hairline_ramp_key, row_weights = meta$hairline_heights,
       hover = meta$hairline_hover, inside = meta$hairline_inside, bare = isTRUE(built@plot@meta$hairline_bare),
       built = built,
       drawing = built@plot@meta$hairline_drawing, table = built@plot@meta$hairline_table,
       min_plot = built@plot@meta$hairline_min_plot,
       aspect = panel_aspect(built), rows = max(vapply(panels, `[[`, numeric(1), "row")),
       columns = max(vapply(panels, `[[`, numeric(1), "col")), title = plot_label(built, "title"),
       subtitle = plot_label(built, "subtitle"), caption = plot_label(built, "caption"),
       y_title = plot_label(built, if (flipped) "x" else "y"), x_title = plot_label(built, if (flipped) "y" else "x"),
       legend = built@plot@meta$hairline_legend %||% c(legend_items(built), reference_legend_items(built)),
       notes = built@plot@meta$hairline_notes %||% list(),
       x_ranges = lapply(built@layout$panel_params, function(params) params$x$continuous_range),
       headers = built@plot@meta$hairline_headers %||% list(),
       references = built@plot@meta$hairline_references %||% list(), line_layers = line_layers(built),
       y_ranges = lapply(built@layout$panel_params, function(params) params$y$continuous_range))
}

panel_header_for <- function(parts, index) {
  # A composed figure resolves each panel's header from the chart it came from.
  if (isTRUE(parts$panels[[index]]$header_set)) return(parts$panels[[index]]$header)
  headers <- parts$headers
  label <- parts$panels[[index]]$label
  if (is.null(label)) return(if (length(parts$panels) == 1 && length(headers)) headers[[1]] else NULL)
  headers[[label]] %||% list(name = label)
}
