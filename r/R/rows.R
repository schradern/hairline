# Composed figures: hairline plots stacked as panel rows of one frame, the R counterpart of the Python package's
# figure(panels=, heights=, sharex=) with charts drawn into it (into=, panel=). Each plot keeps its own panels, axes
# and headers; the frame takes the title, legend row and caption once, sizes the rows by `heights` and labels one
# shared time axis at the bottom.

#' Rows of plots on one time axis
#'
#' Stacks hairline plots as the panel rows of one figure: [hl_lanes()] above
#' [hl_levels()] puts the cause (patients) right above its effect (staff) on
#' one time axis. The figure has one title, subtitle, legend row and caption;
#' each plot keeps its panels, row labels and panel headers. `heights` sizes
#' the panel rows by content, one weight per panel row (a plot with facets
#' gives several rows). With `sharex`, the time-of-day plots share one window
#' and only the bottom row is labelled. The legend row lists every plot's
#' items once and the last binned colour key; each plot's notes (its calendar
#' filter, the quantile rule) follow the caption.
#'
#' @param ... Plots made with hairline (a chart function or [theme_hairline()]), top to bottom.
#' @param heights Relative heights of the panel rows, e.g. `c(9, 3.5, 4.5)`; `NULL` for equal rows.
#' @param sharex Share one time-of-day window and label the x axis once, at the bottom.
#' @param title,subtitle,caption Frame texts of the figure.
#' @param height_mm Figure height in mm; `NULL` for the preset's.
#' @param size Size preset, as in [hl_save()].
#' @return A ggplot with the hairline frame.
#' @examples
#' stays <- data.frame(place = c("Theatre 1", "Theatre 1"), start = c("2026-01-05 08:00", "2026-01-06 09:10"),
#'                     end = c("2026-01-05 10:00", "2026-01-06 11:30"))
#' staff <- data.frame(role = "Doctors", start = stays$start, end = stays$end)
#' hl_rows(hl_lanes(stays, "place", "start", "end"), hl_levels(staff, "start", end = "end", by = "role"),
#'         heights = c(2, 3), title = "Theatre and doctors")
#' @export
hl_rows <- function(..., heights = NULL, sharex = TRUE, title = NULL, subtitle = NULL, caption = NULL,
                    height_mm = NULL, size = "double") {
  plots <- list(...)
  if (!length(plots)) stop("hairline: hl_rows() needs at least one plot", call. = FALSE)
  for (index in seq_along(plots)) {
    if (!S7::S7_inherits(plots[[index]], hairline_plot)) {
      stop(sprintf(paste("hairline: hl_rows(): plot %d is not a hairline plot; add + theme_hairline() or use a",
                         "chart function"), index), call. = FALSE)
    }
  }
  for (weight in heights) check_positive(weight, "heights")
  check_size_preset(size)
  notes <- unlist(lapply(plots, function(plot) plot@meta$hairline_row_notes))
  plot <- ggplot2::ggplot() + ggplot2::labs(title = title, subtitle = subtitle, caption = add_notes(caption, notes)) +
    theme_hairline()
  plot@meta$hairline_rows <- list(plots = plots, heights = heights, sharex = isTRUE(sharex))
  plot@meta$hairline_size <- size
  plot@meta$hairline_height_mm <- height_mm
  plot
}

# The plots of a composition with one shared time-of-day window, when `sharex` asks for it.
shared_time_plots <- function(rows) {
  times <- unlist(lapply(rows$plots, function(plot) plot@meta$hairline_time), recursive = FALSE)
  if (!rows$sharex || !length(times)) return(rows$plots)
  window <- time_window(times)
  lapply(rows$plots, function(plot) {
    if (is.null(plot@meta$hairline_time)) return(plot)
    suppressMessages(plot + time_scale(window))
  })
}

# The frame parts of each plot, built without handing them to a host on their own.
member_parts <- function(plots) {
  previous <- isTRUE(hairline_state$handing_off)
  hairline_state$handing_off <- TRUE
  on.exit(hairline_state$handing_off <- previous)
  lapply(plots, function(plot) {
    frame <- ggplot2::ggplotGrob(plot)
    if (!inherits(frame, "hairline_frame")) stop("hairline: hl_rows(): a plot did not build a hairline frame",
                                                 call. = FALSE)
    frame$parts
  })
}

check_row_heights <- function(heights, rows) {
  if (is.null(heights) || length(heights) == rows) return(invisible())
  stop(sprintf(paste("hairline: heights names %d rows, but the plots make %d panel rows; give one height per row"),
               length(heights), rows), call. = FALSE)
}

# Legend items in plot order, each label once.
merged_legend <- function(members) {
  items <- list()
  for (member in members) {
    for (item in member$legend) {
      if (!item$label %in% vapply(items, `[[`, "", "label")) items[[length(items) + 1]] <- item
    }
  }
  items
}

# The composition's own parts (title, subtitle, caption, settings) with the panels of its plots as rows: each panel
# keeps its axes, row blocks, line layers and resolved header; with `sharex` only the bottom row keeps x labels.
composed_parts <- function(parts, rows) {
  members <- member_parts(shared_time_plots(rows))
  panels <- list()
  inside <- list()
  ranges <- list(x = list(), y = list())
  placed <- list()
  row_offset <- 0
  for (member in members) {
    if (member$columns > 1) stop("hairline: hl_rows(): each plot needs its panels in one column", call. = FALSE)
    offset <- length(panels)
    for (index in seq_along(member$panels)) {
      panel <- member$panels[[index]]
      panel$row <- panel$row + row_offset
      panel["header"] <- list(panel_header_for(member, index))
      panel$header_set <- TRUE
      panel$layers <- member$line_layers
      panels[[length(panels) + 1]] <- panel
    }
    for (label in member$inside) {
      label$panel <- label$panel + offset
      inside[[length(inside) + 1]] <- label
    }
    ranges$x <- c(ranges$x, member$x_ranges)
    ranges$y <- c(ranges$y, member$y_ranges)
    placed[[length(placed) + 1]] <- list(parts = member, panels = offset + seq_along(member$panels))
    row_offset <- row_offset + member$rows
  }
  check_row_heights(rows$heights, row_offset)
  if (rows$sharex) {
    for (index in seq_along(panels)) if (panels[[index]]$row < row_offset) panels[[index]]$axis_b <- ggplot2::zeroGrob()
  }
  keys <- Filter(Negate(is.null), lapply(members, `[[`, "ramp_key"))
  replaced(parts, list(panels = panels, rows = row_offset, columns = 1, bare = FALSE, drawing = NULL, table = NULL,
                       min_plot = NULL, aspect = NULL, y_title = NULL, x_title = NULL, legend = merged_legend(members),
                       notes = list(), headers = list(), references = list(), x_ranges = ranges$x,
                       y_ranges = ranges$y, row_weights = rows$heights,
                       ramp_key = if (length(keys)) keys[[length(keys)]], hover = NULL, inside = inside,
                       members = placed))
}

# `parts` with each of `values` set as given (NULL included), not merged into what was there.
replaced <- function(parts, values) {
  for (name in names(values)) parts[name] <- list(values[[name]])
  parts
}
