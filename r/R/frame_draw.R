# Draw a planned frame: background, panels with their axes, and every frame text.

viewport_pt <- function(x, y, width, height, just) {
  as_unit <- function(value) if (grid::is.unit(value)) value else grid::unit(value, "pt")
  grid::viewport(x = as_unit(x), y = as_unit(y), width = as_unit(width), height = as_unit(height), just = just)
}

baseline_grob <- function(box, bottom, settings) {
  grid::segmentsGrob(grid::unit(box[1], "pt"), grid::unit(bottom, "pt"), grid::unit(box[1] + box[3], "pt"),
                     grid::unit(bottom, "pt"),
                     gp = grid::gpar(col = settings$neutral$axis, lineend = "butt",
                                     lwd = hl_tokens()$lines$axis * settings$base_size / 0.75))
}

one_panel_grobs <- function(panel, box, height, settings, bare = FALSE, layers = logical()) {
  y_pad <- hl_tokens()$spacing$y_labels_plot * settings$base_size
  x_pad <- hl_tokens()$spacing$x_tick_pad * role_size(settings, "label")
  bottom <- height - box[2] - box[4]
  panel$grob <- scale_layer_lines(panel$grob, layers, line_scale(box[3]))
  plot <- grid::gTree(children = grid::gList(panel$grob), vp = viewport_pt(box[1], bottom, box[3], box[4], c(0, 0)))
  if (bare) return(list(plot))
  list(plot, baseline_grob(box, bottom, settings),
       grid::gTree(children = grid::gList(panel$axis_l),
                   vp = viewport_pt(box[1] - y_pad, bottom, grid::grobWidth(panel$axis_l), box[4], c(1, 0))),
       grid::gTree(children = grid::gList(panel$axis_b),
                   vp = viewport_pt(box[1], bottom - x_pad, box[3], grid::grobHeight(panel$axis_b), c(0, 1))))
}

panel_grobs <- function(parts, plan) {
  grobs <- lapply(seq_along(parts$panels), function(index) {
    box <- fitted_box(plan$layout$panels[[index]], parts$aspect)
    panel <- parts$panels[[index]]
    one_panel_grobs(panel, box, plan$size[2], parts$settings, parts$bare, panel$layers %||% parts$line_layers)
  })
  unlist(grobs, recursive = FALSE)
}

line_grobs <- function(lines, baselines, x, style, height) {
  lapply(seq_along(lines), function(index) text_grob_pt(lines[index], x, baselines[index], style, height))
}

header_grobs <- function(parts, plan) {
  grobs <- list()
  for (key in names(plan$composed)) {
    row <- parts$panels[[as.integer(key)]]$row
    baselines <- plan$layout$panel_header_baselines[[row]]
    for (run in plan$composed[[key]]$runs) {
      grobs[[length(grobs) + 1]] <- text_grob_pt(run$text, run$x, baselines[run$line + 1], run$style, plan$size[2])
    }
  }
  grobs
}

axis_title_grobs <- function(parts, plan) {
  style <- role_style(parts$settings, "label")
  grobs <- list()
  if (!is.null(parts$y_title)) {
    grobs[[1]] <- text_grob_pt(parts$y_title, plan$layout$y_title_left, plan$layout$y_title_baseline, style,
                               plan$size[2])
  }
  if (!is.null(parts$x_title)) {
    right <- max(vapply(plan$layout$panels[seq_along(parts$panels)], function(box) box[1] + box[3], numeric(1)))
    grobs[[length(grobs) + 1]] <- text_grob_pt(parts$x_title, right, plan$layout$x_title_baseline, style,
                                               plan$size[2], "right")
  }
  for (index in seq_along(parts$panels)) {
    title <- panel_header_for(parts, index)$x_title
    if (is.null(title)) next
    box <- plan$layout$panels[[index]]
    baseline <- plan$layout$x_title_row_baselines[[parts$panels[[index]]$row]]
    grobs[[length(grobs) + 1]] <- text_grob_pt(title, box[1] + box[3], baseline, style, plan$size[2], "right")
  }
  grobs
}

frame_children <- function(parts, plan) {
  settings <- parts$settings
  height <- plan$size[2]
  layout <- plan$layout
  surface <- if (identical(settings$background, "transparent")) NA else settings$background
  grobs <- c(list(grid::rectGrob(gp = grid::gpar(fill = surface, col = NA))), panel_grobs(parts, plan),
             drawing_grobs(plan$shapes, height, settings),
             line_grobs(plan$texts$title, layout$title_baselines, layout$left, role_style(settings, "title"), height),
             line_grobs(plan$texts$subtitle, layout$subtitle_baselines, layout$left, role_style(settings, "subtitle"),
                        height),
             line_grobs(plan$texts$caption, layout$caption_baselines, layout$left, role_style(settings, "caption"),
                        height),
             legend_grobs(plan$placed, layout$legend_row_centers, role_style(settings, "label"), settings$base_size,
                          height, font_metrics()$cap_height,
                          line_scale(fitted_box(layout$panels[[1]], parts$aspect)[3]), settings$neutral$axis,
                          settings$neutral$surface),
             header_grobs(parts, plan), axis_title_grobs(parts, plan), table_grobs(parts, plan),
             reference_grobs(parts, plan),
             note_grobs(parts, plan), block_grobs(parts, plan), inside_grobs(parts, plan),
             side_number_grobs(parts, plan))
  do.call(grid::gList, grobs)
}

# Each row block's name at the left of its panel's label column, on the baseline of the block's first row.
block_grobs <- function(parts, plan) {
  settings <- parts$settings
  surface <- surface_colour(settings)
  cap <- font_metrics()$cap_height
  grobs <- list()
  for (index in seq_along(parts$panels)) {
    panel <- parts$panels[[index]]
    if (!length(panel$blocks)) next
    box <- plan$layout$panels[[index]]
    left <- if (panel$col == 1) plan$layout$left else
      box[1] - hl_tokens()$spacing$y_labels_plot * settings$base_size - plan$texts$column_widths[panel$col]
    range <- parts$y_ranges[[index]]
    position <- sum(vapply(panel$blocks, `[[`, numeric(1), "count")) - 1
    for (block in panel$blocks) {
      style <- block_style(settings, point_fill(block$colour, surface))
      centre <- box[2] + (range[2] - position) / diff(range) * box[4]
      grobs[[length(grobs) + 1]] <- text_grob_pt(block$name, left, centre + style$size * cap / 2, style, plan$size[2])
      position <- position - block$count
    }
  }
  grobs
}

# Each numbers column beside its panel, the label faint and the value muted, as spread's key numbers.
side_number_grobs <- function(parts, plan) {
  settings <- parts$settings
  cap <- font_metrics()$cap_height
  gap <- hl_tokens()$spacing$y_labels_plot * settings$base_size
  plain <- role_style(settings, "label", NULL, settings$neutral$faint)
  strong <- role_style(settings, "label", hl_tokens()$type$value_weight, settings$neutral$muted)
  grobs <- list()
  for (index in seq_along(parts$panels)) {
    box <- plan$layout$panels[[index]]
    range <- parts$y_ranges[[index]]
    for (entry in parts$panels[[index]]$side_numbers) {
      baseline <- box[2] + (range[2] - entry$position) / diff(range) * box[4] + plain$size * cap / 2
      x <- box[1] + box[3] + gap
      grobs[[length(grobs) + 1]] <- text_grob_pt(paste0(entry$label, " "), x, baseline, plain, plan$size[2])
      grobs[[length(grobs) + 1]] <- text_grob_pt(entry$value, x + side_pair_width(settings, entry$label, ""),
                                                 baseline, strong, plan$size[2])
    }
  }
  grobs
}

# Labels inside bars (swimlanes, stacked segments) show only where their bar holds them: along the bar (its length,
# less a pad either side) and across it (its thickness, when given). As Python's fit_inside_labels().
inside_fits <- function(label, box, x_range, y_range, style, pad) {
  metrics <- font_metrics()
  tall <- style$size * (metrics$cap_height + metrics$descender)
  wide <- text_width_pt(label$text, style)
  vertical <- isTRUE(label$vertical)
  along <- (label$end - label$start) / diff(if (vertical) y_range else x_range) * (if (vertical) box[4] else box[3])
  fits <- (if (vertical) tall else wide) <= along - 2 * pad
  if (!is.null(label$thickness)) {
    across <- label$thickness / diff(if (vertical) x_range else y_range) * (if (vertical) box[3] else box[4])
    fits <- fits && (if (vertical) wide else tall) <= across
  }
  fits
}

inside_grobs <- function(parts, plan) {
  settings <- parts$settings
  cap <- font_metrics()$cap_height
  pad <- hl_tokens()$swimlanes$label_pad * settings$base_size
  grobs <- list()
  for (label in parts$inside %||% list()) {
    box <- plan$layout$panels[[label$panel]]
    x_range <- parts$x_ranges[[label$panel]]
    y_range <- parts$y_ranges[[label$panel]]
    style <- role_style(settings, "label", NULL, label$colour)
    if (!inside_fits(label, box, x_range, y_range, style, pad)) next
    middle <- (label$start + label$end) / 2
    if (isTRUE(label$vertical)) {
      x <- box[1] + (label$at - x_range[1]) / diff(x_range) * box[3]
      centre <- box[2] + (y_range[2] - middle) / diff(y_range) * box[4]
    } else {
      x <- box[1] + (middle - x_range[1]) / diff(x_range) * box[3]
      centre <- box[2] + (y_range[2] - (label$y %||% label$at)) / diff(y_range) * box[4]
    }
    grobs[[length(grobs) + 1]] <- text_grob_pt(label$text, x, centre + style$size * cap / 2, style, plan$size[2],
                                               "center")
  }
  grobs
}

reference_grobs <- function(parts, plan) {
  style <- role_style(parts$settings, "caption")
  gap <- hl_tokens()$reference$label_gap * style$size
  grobs <- list()
  for (reference in parts$references) {
    if (is.null(reference$label)) next
    if (is.null(reference$y)) {
      grobs <- c(grobs, vertical_reference_grobs(reference, parts, plan, style, gap))
      next
    }
    for (index in seq_along(parts$panels)) {
      box <- plan$layout$panels[[index]]
      range <- parts$y_ranges[[index]]
      line_y <- box[2] + (1 - (reference$y - range[1]) / diff(range)) * box[4]
      below <- reference_label_below(reference$y, range, box[4], style$size, parts$settings$base_size)
      baseline <- if (below) line_y + gap + style$size * font_metrics()$cap_height else line_y - gap
      grobs[[length(grobs) + 1]] <- text_grob_pt(reference$label, box[1] + box[3], baseline, style, plan$size[2],
                                                 "right")
    }
  }
  grobs
}

# A vertical line's label at the top of each panel, right of the line, as Python places it.
vertical_reference_grobs <- function(reference, parts, plan, style, gap) {
  lapply(seq_along(parts$panels), function(index) {
    box <- plan$layout$panels[[index]]
    range <- parts$x_ranges[[index]]
    x <- box[1] + (as.numeric(reference$x) - range[1]) / diff(range) * box[3] + gap
    text_grob_pt(reference$label, x, box[2] + gap + style$size * font_metrics()$cap_height, style, plan$size[2])
  })
}

note_grobs <- function(parts, plan) {
  style <- role_style(parts$settings, "caption")
  gap <- hl_tokens()$reference$label_gap * style$size
  grobs <- list()
  for (note in parts$notes) {
    for (index in seq_along(parts$panels)) {
      if (!is.null(note$panels) && !isTRUE(parts$panels[[index]]$label %in% note$panels)) next
      box <- plan$layout$panels[[index]]
      range <- parts$x_ranges[[index]]
      x <- box[1] + (as.numeric(note$x) - range[1]) / diff(range) * box[3] + gap
      baseline <- box[2] + box[4] - gap
      grobs[[length(grobs) + 1]] <- text_grob_pt(note$label, x, baseline, style, plan$size[2])
    }
  }
  grobs
}

warn_dropped <- function(plan) {
  for (key in names(plan$composed)) {
    dropped <- plan$composed[[key]]$dropped
    if (length(dropped)) {
      warning(sprintf("hairline: panel %d header: key numbers dropped because they do not fit: %s",
                      as.integer(key) - 1L, paste(dropped, collapse = ", ")), call. = FALSE)
    }
  }
}

# The R twin of the Python HairlineLayoutError: the figure cannot be laid out as requested.
layout_error <- function(message) {
  structure(class = c("hairline_layout_error", "error", "condition"), list(message = message, call = NULL))
}

# hl_save() refuses a frame that cannot be laid out before it draws (fitted_size_mm()); drawn by ggplot2 itself
# (print, ggsave, a viewer window that can still be resized) the plot is drawn without the frame, with a warning.
#' @export
makeContent.hairline_frame <- function(x) {
  alias_base_device_fonts(x$parts$settings$font)
  size <- c(grid::convertWidth(grid::unit(1, "npc"), "pt", valueOnly = TRUE),
            grid::convertHeight(grid::unit(1, "npc"), "pt", valueOnly = TRUE))
  plan <- tryCatch(plan_frame(x$parts, size), error = function(error) {
    warning(sprintf("%s; drawing the plot without the hairline frame", conditionMessage(error)), call. = FALSE)
    NULL
  })
  if (is.null(plan)) return(grid::setChildren(x, grid::gList(x$table)))
  warn_dropped(plan)
  grid::setChildren(x, frame_children(x$parts, plan))
}
